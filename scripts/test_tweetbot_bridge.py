"""The opt-in bridge must not change existing routes or expose credentials."""
import http.client
import importlib.util
import json
import os
from pathlib import Path
import sys
import threading
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "outputs"))
spec = importlib.util.spec_from_file_location("circlematch_bridge_test", ROOT / "outputs/circlematch_db_app.py")
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)


class BridgeRouteTests(unittest.TestCase):
    def test_private_route_and_existing_health_endpoint(self):
        with patch.dict(os.environ, {"TWEETBOT_BRIDGE_KEY": "b" * 64, "TWEETBOT_BRIDGE_ENABLED": "true"}), \
             patch.object(app, "summary", return_value={"circles": 123}):
            server = app.ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            try:
                for path, expected in (("/healthz", 200), ("/_tweet-bot/status", 401)):
                    conn = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
                    conn.request("GET", path)
                    response = conn.getresponse()
                    self.assertEqual(response.status, expected)
                    result = json.loads(response.read())
                    if expected == 200:
                        self.assertEqual(result, {"ok": True, "circles": 123})
                    conn.close()
                with patch("chatgpt_bridge.operate", return_value={"status": "ready"}) as operate:
                    conn = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
                    conn.request("POST", "/_tweet-bot/status", "{}",
                                 {"Authorization": "Bearer " + "b" * 64, "Content-Type": "application/json"})
                    response = conn.getresponse()
                    self.assertEqual(response.status, 200)
                    self.assertEqual(json.loads(response.read()), {"status": "ready"})
                    operate.assert_called_once()
                    conn.close()
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=5)


if __name__ == "__main__":
    unittest.main()
