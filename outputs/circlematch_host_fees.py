"""Owner-only success-fee disclosure and exact participation forecasts."""
import html
from urllib.parse import quote

import circlematch_event_pricing as pricing
from circlematch_payments import FEE_BPS


POLICY_VERSION = 'success-fee-20261101'


def fee(amount):
    if isinstance(amount, bool) or not isinstance(amount, int) or amount < 0:
        raise ValueError('金額は0以上の整数円で指定してください')
    return (amount * FEE_BPS + 9999) // 10000


def estimate(event, applications, orders=()):
    """Admission forecasts are never reported as collected funds or an invoice."""
    event = dict(event)
    gross = 0
    unknown = 0
    count = 0
    for application in applications:
        application = dict(application)
        if application['status'] != 'confirmed':
            continue
        count += 1 if event.get('participation_type') == 'team' and event.get('capacity_unit') == 'チーム' else int(application['participant_count'])
        amount = pricing.amount_due(event, application)
        if amount is None:
            unknown += 1
        else:
            gross += amount
    withheld = sum(max(0, int(order['fee']) - int(order['fee_refunded']))
                   for order in map(dict, orders)
                   if order.get('paid_at') and order.get('mode') == 'live')
    if event['status'] == 'cancelled':
        state, label = 'cancelled', '開催中止・利用料対象外'
    elif event['status'] == 'draft':
        state, label = 'draft', '下書き・成立前'
    elif not event.get('minimum_participants'):
        state, label = 'unconfigured', '最低開催数の設定待ち'
    elif not event.get('announcement_version'):
        state, label = 'pending', '仮成立・主催者の開催決定待ち' if count >= event['minimum_participants'] else '最低開催数に向けて募集中'
    elif count < event['minimum_participants']:
        state, label = 'review', '最低開催数未達・開催可否の再確認待ち'
    else:
        state, label = 'announced', '開催決定済み'
    proposed = None if unknown else fee(gross)
    eligible = state == 'announced'
    return dict(policy_version=POLICY_VERSION, preview_only=True, billing_enabled=False,
                state=state, state_label=label, fee_bps=FEE_BPS,
                forecast_gross=None if unknown else gross, incomplete_applications=unknown,
                forecast_fee=proposed, online_fee_withheld=withheld,
                proposed_additional_fee=(None if proposed is None else max(0, proposed - withheld) if eligible else 0),
                charge_due=None, explanation='受付確定分からの試算です。入金額・請求額ではありません。')


STYLE = '''<style>
.host-fee-note{border-left:3px solid #187551;padding:12px 16px;background:#f0f8f3;margin:16px 0;color:#25372d;line-height:1.65}
.host-fee-note h2,.host-fee-note h3{font-size:16px;margin:0 0 8px;letter-spacing:0}
.host-fee-note p{margin:6px 0}.host-fee-badge{font-size:12px;font-weight:700;color:#476151}
.host-fee-page{max-width:760px;margin:0 auto;padding:24px 16px}.host-fee-page h1{font-size:24px;letter-spacing:0}
.host-fee-page h2{font-size:18px;letter-spacing:0}.host-fee-page p{line-height:1.7}
.host-fee-totals{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:0;margin:20px 0}
.host-fee-totals dt,.host-fee-totals dd{padding:13px 0;border-bottom:1px solid #dce6de;margin:0;overflow-wrap:anywhere}
.host-fee-totals dd{text-align:right;font-weight:700;padding-left:16px;font-variant-numeric:tabular-nums}
.host-fee-unit{display:block;padding:8px 0;border-top:1px solid #dce6de;font-size:14px}
@media(max-width:480px){.host-fee-page{padding:16px 12px}.host-fee-page h1{font-size:22px}.host-fee-totals{font-size:14px}.host-fee-note{padding:12px}}
</style>'''


def notice(*, event_id='', heading='大会成立時の主催者利用料', compact=False):
    link = (f'<p><a href="/events/{quote(event_id, safe="")}/host-fee">利用料の試算を確認する</a></p>'
            if event_id else '')
    description = ('最低開催数に達し、主催者が開催を決定すると利用料の対象になります。'
                   '募集掲載・仮成立の時点では発生しません。未入金分は売上に数えません。')
    return ('<section class="host-fee-note" data-host-fee-private>'
            '<span class="host-fee-badge">主催者のみ</span>'
            + f'<h{3 if compact else 2}>{html.escape(heading)}</h{3 if compact else 2}>'
            '<p>成立した有料大会の参加費売上に対する利用料 <strong>10%</strong></p>'
            + ('' if compact else '<p>' + description + '</p>')
            + '<p>参加者への追加請求はありません。Circle Matchへの利用料の支払いは主催者が行います。</p>'
            + link + '</section>')


def legacy_notice(event_id=''):
    link = f'<p><a href="/events/{quote(event_id,safe="")}/host-fee">利用料の条件と適用可否を確認する</a></p>' if event_id else ''
    return '<section class="host-fee-note" data-host-fee-private><h3>既存大会の主催者利用料は免除</h3><p>この大会には徴収再開後も遡って利用料を適用しません。</p>' + link + '</section>'


def form_notice(*, require_consent=True, legacy=False):
    if legacy:
        return STYLE + legacy_notice()
    consent = (f'<label class="publication-consent"><input type="checkbox" id="hostFeeConsent" data-policy-version="{POLICY_VERSION}" required> '
               '有料大会は主催者の開催決定後、参加費売上の10%をCircle Matchに支払うことに同意します。'
               '未入金分・無料大会・中止は対象外、オンライン決済の控除分は重複請求しません。</label>') if require_consent else ''
    return STYLE + notice() + '<output id="hostFeeUnitPreview" aria-live="polite"></output>' + consent


FORM_SCRIPT = r'''<script>(()=>{
const output=document.getElementById('hostFeeUnitPreview'), form=document.getElementById('eventForm');
if(!output||!form)return;
const money=n=>n.toLocaleString('ja-JP')+'円';
function read(id){const input=document.getElementById(id);if(!input||input.disabled||input.closest('[hidden]'))return null;
const value=input.value.normalize('NFKC').replace(/[,\s]/g,'');return /^[0-9]{1,10}$/.test(value)?BigInt(value):null}
function update(){output.replaceChildren();const both=document.getElementById('participation_type').value==='both'&&!document.getElementById('individual_fee_amount').disabled;
const kinds=both?[['individual_fee_amount','個人1人'],['team_fee_amount','1チーム']]:[['fee_amount',document.getElementById('participation_type').value==='team'?'1チーム':'個人1人']];
const consent=document.getElementById('hostFeeConsent');if(consent)consent.required=!kinds.every(([id])=>read(id)===0n);
if(document.getElementById('payment_method').value==='online'){output.textContent='オンライン決済で控除される利用料と重複して請求しない設計です。';return}
for(const [id,label] of kinds){const gross=read(id);if(gross===null)continue;const amount=(gross*1000n+9999n)/10000n,p=document.createElement('span');p.className='host-fee-unit';
p.textContent=label+' '+money(gross)+' → 利用料試算 '+money(amount)+' / 主催者受取見込 '+money(gross-amount);output.append(p)}}
form.addEventListener('input',update);form.addEventListener('change',update);update();
})();</script>'''


def render(event, estimate):
    import circlematch_payment_ui as payment_ui
    event_id = quote(event['event_id'], safe='')
    money = lambda n: '未確定' if n is None else f'{n:,}円'
    lines = [('受付確定分の参加費見込', money(estimate['forecast_gross'])),
             ('入金確認済みの参加費売上', money(estimate['collected_gross'])),
             ('主催者利用料（免除）' if estimate.get('fee_waived') else '成立後の利用料（売上の10%）', money(estimate['fee_total'])),
             ('オンライン決済で控除確認済み', money(estimate['online_fee_withheld'])),
             ('Circle Matchへの利用料支払済み', money(estimate['fee_paid'])),
             ('今回のお支払額', money(estimate['charge_due']))]
    actions = ''
    if estimate['mode'] == 'test':
        actions += '<p class="host-fee-note">テストモードです。実際の請求・送金は行いません。</p>'
    if estimate.get('fee_waived'):
        actions += '<p class="host-fee-note">この大会の主催者利用料は0円です。徴収を再開しても後から請求しません。</p>'
    elif estimate['legacy_event']:
        actions += '<h3>この大会への適用は任意です</h3><p>同意しなくても、今の募集・受付はそのまま続けられます。</p>'
        if estimate['opt_in_blocker']:
            actions += '<p>' + html.escape(estimate['opt_in_blocker']) + '</p>'
        else:
            actions += payment_ui.action('/api/payments/host-fees/'+event_id+'/opt-in', 'この大会に利用料を適用する',
                fields='<label class="payment-consent"><input type="checkbox" name="accepted" required>参加費はまだ受け取っていません。開催を決定した場合、入金確認済みの参加費売上の10%を主催者として支払うことに同意します。</label>',
                values={'policy_version':POLICY_VERSION})
            actions += '<p>この操作では決済・引き落としは行いません。</p>'
    elif not estimate['agreement_accepted']:
        actions += '<p>公開前の主催者利用料への同意待ちです。</p>'
    else:
        actions += '<p>主催者利用料の条件に同意済みです。</p>'
    if estimate['refund_review_amount']:
        actions += '<p class="host-fee-note">利用料の返金・精算確認が必要です：' + money(estimate['refund_review_amount']) + '。重ねて支払わず、運営へ連絡してください。自動返金の完了を示すものではありません。</p>'
    if not estimate['billing_enabled'] and not estimate.get('fee_waived'):
        actions += '<p class="host-fee-note">主催者利用料の新規支払いは停止中です。既存の入金・支払状況の照合は継続します。</p>'
    elif estimate['charge_due'] is not None and estimate['charge_due'] >= 50:
        actions += payment_ui.action('/api/payments/host-fees/'+event_id+'/checkout','Stripeの利用料支払確認へ',
            values={'quote_token':estimate['quote_token']},confirm=True)
        actions += '<p>次のStripe画面で支払いを確定します。この画面を開いただけでは課金されません。</p>'
    elif estimate['charge_due']:
        actions += '<p>50円未満の利用料は決済下限未満です。追加売上があるまで決済を作りません。運営と精算をご確認ください。</p>'
    if estimate['pending_order'] or estimate['fee_paid']:
        actions += payment_ui.action('/api/payments/host-fees/'+event_id+'/reconcile','利用料の支払状況を更新する')
    if estimate['pending_order'] and estimate['pending_order']['state'] == 'review':
        actions += '<p class="host-fee-note" role="alert">利用料の決済照合に確認が必要です。重ねて支払わず運営へご連絡ください。</p>'
    return (STYLE + '<section class="host-fee-page" data-host-fee-private>'
            f'<a href="/mypage?tab=hosted">主催するイベントへ</a><h1>大会成立時の利用料</h1>'
            f'<p>{html.escape(event["title"])}</p><span class="host-fee-badge">主催者のみ / 利用料{"0円・免除" if estimate.get("fee_waived") else "10%"}</span>'
            f'<h2>{html.escape(estimate["state_label"])}</h2>'
            '<p>最低開催数に到達しただけでは仮成立です。主催者が開催を決定した大会だけが利用料の対象です。</p>'
            '<dl class="host-fee-totals">' + ''.join(f'<dt>{html.escape(k)}</dt><dd>{v}</dd>' for k, v in lines) + '</dl>'
            '<p>受付確定分の見込と、入金確認済みの売上は別です。未入金分を利用料の請求対象にしません。'
            '返金中・料金不明・決済要確認のときは、照合するまで追加決済できません。</p>'
            '<h2>主催者への料金案内</h2><p>' +
            ('この大会は利用料の免除対象です。開催確定後や徴収再開後も主催者利用料は0円です。' if estimate.get('fee_waived') else
             '募集掲載・仮成立の段階は利用料なし。無料大会・開催中止は0円。'
             '売上は確認済みの参加費から返金分を除いて計算し、利用料10%は1円未満切り上げです。') + '</p>'
            '<p>参加費の口座振込・現地払いは主催者への支払いです。Circle Matchへの利用料の支払いとは別です。'
            'オンライン決済で控除済みの利用料は追加決済から差し引き、重複して請求しません。</p>'
            + actions +
            f'<a class="button" href="/events/{event_id}/organize">開催案内へ</a></section>')
