"""Browser-local preferences. No account data or notification consent is changed."""
from hashlib import sha256
from html import escape
from pathlib import Path

STATIC = Path(__file__).resolve().parent / 'settings_static'
ASSET_PATHS = {
    '/assets/settings/preferences.js': (STATIC / 'preferences.js', 'application/javascript; charset=utf-8'),
    '/assets/settings/preferences.css': (STATIC / 'preferences.css', 'text/css; charset=utf-8'),
}


def decorate(body):
    page = body.decode('utf-8') if isinstance(body, bytes) else body
    head = ''
    for url, (path, _) in ASSET_PATHS.items():
        versioned = f'{url}?v={sha256(path.read_bytes()).hexdigest()[:12]}'
        head += f'<script src="{versioned}"></script>' if url.endswith('.js') else f'<link rel="stylesheet" href="{versioned}">'
    return page.replace('</head>', head + '</head>', 1).encode('utf-8')


def render_body(return_to='/'):
    return f'''<div class="cm-preferences">
<a class="cm-settings-back" href="{escape(return_to, quote=True)}">← 元の画面へ戻る</a>
<h1>設定</h1><p class="cm-settings-note">このブラウザに保存されます。他の端末やアカウント設定には影響しません。</p>
<form id="cm-preferences-form"><fieldset disabled><legend>画面表示</legend>
<div class="cm-view-options">
<label><input type="radio" name="view" value="auto" checked><span>自動</span></label>
<label><input type="radio" name="view" value="mobile"><span>スマホビュー</span></label>
<label><input type="radio" name="view" value="desktop"><span>PCビュー</span></label></div>
<p class="cm-settings-note">保存後、元の画面に戻ると適用されます。設定画面は自動表示です。</p>
</fieldset><fieldset disabled><legend>会場検索</legend><div class="cm-setting-fields">
<label><span>最初に表示するエリア</span><select name="venueArea"><option value="">都内すべて</option><option>23区</option><option>多摩</option><option>島しょ</option></select></label>
<label><span>最初の並び順</span><select name="venueSort"><option value="name">施設名の順</option><option value="price">コート1面1時間の安い順</option></select></label></div>
<label class="cm-remember-setting"><input type="checkbox" name="rememberVenueSearch"><span>前回の会場検索条件を引き継ぐ</span></label>
<p class="cm-settings-note">共有リンクの条件がある場合は、リンクの条件を優先します。</p>
</fieldset><div class="cm-settings-actions"><button type="submit" disabled>設定を保存</button><button type="button" id="cm-settings-reset" disabled>初期設定に戻す</button></div>
<p id="cm-settings-status" role="status" aria-live="polite"></p>
<noscript><p>設定の変更にはJavaScriptを有効にしてください。施設一覧はそのまま閲覧できます。</p></noscript></form></div>'''
