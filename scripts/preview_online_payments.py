"""Loopback-only mock preview. Disposable DB; no real Stripe or email worker."""
import argparse
import html
from http.server import ThreadingHTTPServer
import threading
from urllib.parse import parse_qs, urlparse, urlencode, quote

from test_online_payments import PaymentTests


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--port",type=int,default=8896)
    args=parser.parse_args()
    PaymentTests.setUpClass()
    fixture=PaymentTests()
    fixture.setUp()
    app=fixture.app
    app.SITE_BASE_URL=f"http://127.0.0.1:{args.port}"
    eid=fixture.save(title="【ローカル検証】ピックルボール交流会")
    aid=fixture.apply(eid,3)
    _,_,paid=fixture.paid(title="【ローカル検証】支払確認済みの交流会")
    with app.connect() as conn:
        sessions={uid:app.create_user_session(conn,uid) for uid in ("host","person")}
    links={"participant":"/payments/applications/"+aid,"receipt":"/payments/orders/"+paid["order_id"],
           "host":"/events/new?event_id="+eid,"connect":"/payments/connect","payments":"/payments",
           "cancel":"/payments/cancel/"+paid["event_id"],"home":"/events"}

    class PreviewHandler(app.Handler):
        def do_GET(self):
            parsed=urlparse(self.path)
            if parsed.path=="/preview":
                items=''.join('<li><a href="/preview/open?'+urlencode({"screen":name,"as":"person" if name in {"participant","receipt"} else "host"})+'">'+html.escape(name)+'</a></li>' for name in links)
                self.send_html(('<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><h1>ローカル決済プレビュー</h1><p>隔離DB・モックです。実際の課金・メール送信はありません。</p><ul>'+items+'</ul>').encode())
            elif parsed.path=="/preview/open":
                query=parse_qs(parsed.query)
                uid=query.get("as",["person"])[0]
                screen=query.get("screen",["participant"])[0]
                self.send_response(303)
                self.send_header("Set-Cookie","cm_session="+sessions[uid]+"; Path=/; HttpOnly; SameSite=Lax")
                self.send_header("Location",quote(links[screen],safe="/?=&"));self.end_headers()
            elif parsed.path=="/preview/stop":
                self.send_html(b"Preview stopped")
                threading.Thread(target=server.shutdown,daemon=True).start()
            else:
                super().do_GET()

    server=ThreadingHTTPServer(("127.0.0.1",args.port),PreviewHandler)
    print(app.SITE_BASE_URL+"/preview",flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close();fixture.tearDown();PaymentTests.tearDownClass()


if __name__=="__main__":
    main()
