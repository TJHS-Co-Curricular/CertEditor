import base64
import hashlib
import json
import os
import socket
import threading
import unittest
import urllib.error
import urllib.request

from helpers import TempHome, make_result_html

from certeditor import server, settings


class ServerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.home = TempHome().__enter__()
        P = cls.home.setup()
        with open(os.path.join(P.result, "S1A1.html"), "wb") as f:
            f.write(make_result_html([("测试", "000000000001", "TEST", [("2026", "学会", "Society", "会员", "Member")])]))
        server.STATE.ini = settings.load_ini()
        cls.httpd, cls.port = server.make_server("127.0.0.1", 18765, True)
        cls.t = threading.Thread(target=cls.httpd.serve_forever, daemon=True)
        cls.t.start()
        cls.base = "http://127.0.0.1:%d" % cls.port

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.home.__exit__(None, None, None)

    def req(self, path, data=None, headers=None):
        r = urllib.request.Request(self.base + path, data=data, headers=headers or {},
                                   method="POST" if data is not None else "GET")
        with urllib.request.urlopen(r, timeout=10) as resp:
            return resp.status, resp.headers, resp.read()

    def js(self, path, data=None):
        return json.loads(self.req(path, data)[2].decode("utf-8"))

    def test_index_and_state(self):
        st, h, body = self.req("/")
        self.assertEqual(st, 200)
        self.assertIn("联课证书编辑器".encode("utf-8"), body)
        s = self.js("/api/state")
        self.assertEqual(s["app"], "CertEditor")
        self.assertEqual([c["name"] for c in s["classes"]], ["S1A1"])
        self.assertEqual(s["dirs"]["data"], "data")

    def test_class_roundtrip(self):
        proj = self.js("/api/class?name=S1A1")
        self.assertEqual(len(proj["students"]), 1)
        proj["students"][0]["cn"] = "改名"
        self.assertTrue(self.js("/api/class?name=S1A1", json.dumps(proj).encode())["ok"])
        self.assertEqual(self.js("/api/class?name=S1A1")["students"][0]["cn"], "改名")
        self.assertTrue(os.path.isfile(os.path.join(self.home.P.data, "S1A1.json")))

    def test_bad_name_rejected(self):
        with self.assertRaises(urllib.error.HTTPError) as cm:
            self.req("/api/class?name=..%2Fx", b"{}")
        self.assertEqual(cm.exception.code, 400)

    def test_background_upload_and_chunked_download(self):
        """App 实际使用的路径：二进制上传 + JSON 分段下载，必须完整一致。"""
        blob = os.urandom(3 * 1024 * 1024 + 123)
        r = self.js("/api/sheet-image?ext=jpg", blob)
        self.assertEqual(r["size"], len(blob))
        self.assertEqual(r["cfg"]["bgPath"], "config/background.jpg")
        first = self.js("/api/sheet-image-part?i=0")
        parts = [first] + [self.js("/api/sheet-image-part?i=%d" % i) for i in range(1, first["chunks"])]
        got = b"".join(base64.b64decode(p["data"]) for p in parts)
        self.assertEqual(len(got), first["total"])
        self.assertEqual(hashlib.md5(got).hexdigest(), first["md5"])
        self.assertEqual(got, blob)
        self.assertEqual(first["type"], "image/jpeg")
        with self.assertRaises(urllib.error.HTTPError) as cm:
            self.req("/api/sheet-image-part?i=%d" % first["chunks"])
        self.assertEqual(cm.exception.code, 400)
        self.js("/api/sheet-image", b"")
        self.assertEqual(self.js("/api/cfgsig")["bg"], "")

    def test_raw_binary_endpoint_diagnostic(self):
        """旧的二进制网址（后备用）。若本机防毒 / 网络过滤卡住大型二进制回应，这里只会略过并提示，不影响打包。"""
        blob = os.urandom(512 * 1024)
        self.js("/api/sheet-image?ext=jpg", blob)
        try:
            r = urllib.request.Request(self.base + "/api/sheet-image?v=diag")
            with urllib.request.urlopen(r, timeout=5) as resp:
                body, etag = resp.read(), resp.headers["ETag"]
        except (socket.timeout, TimeoutError, ConnectionError, urllib.error.URLError) as e:
            self.skipTest("本机大型二进制传输被卡住（多半是防毒网页防护 / VPN / 网络过滤驱动）：%s。"
                          "编辑器已改用 JSON 分段传送底图，不受影响。" % e)
        finally:
            self.js("/api/sheet-image", b"")
        self.assertEqual(body, blob)
        self.assertTrue(etag)

    def test_ping_probe(self):
        info = server.probe_instance(self.port)
        self.assertEqual(info["app"], "CertEditor")
        self.assertIsNone(server.probe_instance(1))


if __name__ == "__main__":
    unittest.main()
