"""Public operator contact UI. It composes mail locally and never sends mail."""
import html
import re
from urllib.parse import quote

BODY = "お問い合わせ内容：\r\n\r\nお使いの端末・ブラウザー（任意）：\r\n\r\n※パスワードやカード情報などは送らないでください。"

def mailto_url(app_name, email):
    email = str(email).strip()
    if not re.fullmatch(r'[^\s@<>"(),;:\\/?#&=]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', email):
        return ""
    name = re.sub(r"[\r\n]", " ", str(app_name)).strip()[:80]
    return "mailto:" + email + "?subject=" + quote("[" + name + "] お問い合わせ", safe="") + "&body=" + quote(BODY, safe="")

def footer(app_name, email):
    href = mailto_url(app_name, email)
    mail = ('<a href="' + html.escape(href, quote=True) + '">' + html.escape(str(email)) + '</a>') if href else ""
    return ('<footer style="max-width:1180px;margin:24px auto;padding:16px;line-height:1.8">'
            '<nav aria-label="運営へのお問い合わせ"><a href="/contact">お問い合わせ・使い方の相談</a> '
            + mail + '</nav></footer>')

def contact_card(app_name, email):
    href = mailto_url(app_name, email)
    if not href:
        return '<p role="status">メール窓口を表示できません。時間をおいてご確認ください。</p>'
    return ('<section id="business-contact" aria-label="メールでお問い合わせ">'
            '<label for="business-contact-email">問い合わせメールアドレス</label><br>'
            '<input id="business-contact-email" type="text" readonly value="' + html.escape(str(email).strip(), quote=True) + '" style="box-sizing:border-box;width:100%;max-width:440px;padding:10px">'
            '<p><a href="' + html.escape(href, quote=True) + '">メールで問い合わせる</a> '
            '<button id="business-contact-copy" type="button" style="min-height:44px">メールアドレスをコピー</button></p>'
            '<p>メールアプリが開きます。内容を入力して送信してください。</p>'
            '<p>メールアプリが開かない場合は、アドレスをコピーしてご利用ください。パスワードやカード情報などは送らないでください。</p>'
            '<p id="business-contact-status" role="status"></p></section>'
            '<script>(()=>{const button=document.getElementById("business-contact-copy");'
            'const address=document.getElementById("business-contact-email");'
            'const status=document.getElementById("business-contact-status");'
            'button.addEventListener("click",async()=>{status.textContent="";try{'
            'if(!navigator.clipboard?.writeText)throw new Error("Clipboard unavailable");'
            'await navigator.clipboard.writeText(address.value);status.textContent="メールアドレスをコピーしました。";'
            '}catch{address.focus();address.select();status.textContent="コピーできませんでした。メールアドレス欄を選択してコピーしてください。";}});})();</script>')
