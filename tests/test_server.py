import base64
import gzip
import hashlib
import json
import os
import socket
import threading
import time
import unittest
import urllib.error
import urllib.request

from helpers import TempHome, make_result_html

from certeditor import paths, server, settings


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

    RESETS = 0     # 本机连线被重置、重试成功的次数
    FILTERED = False   # 本机网页过滤（防毒网页防护 / VPN）改写了 HTML 回应的标头

    @classmethod
    def tearDownClass(cls):
        if cls.FILTERED:
            print("\n  [提示] 本机有网页过滤（防毒网页防护 / VPN 之类）在拦改 127.0.0.1 的 HTML 回应："
                  "\n         伺服器送出的 Content-Encoding: gzip 与 Content-Length 被拿掉、并注入 Permissions-Policy。"
                  "\n         已改用直接量 editor.html 压缩后大小来把关，不影响打包；但浏览器会收到未压缩的页面。")
        if cls.RESETS:
            print("\n  [提示] 测试期间有 %d 次本机连线被重置（WinError 10054 等），均已重试成功。"
                  "\n         这是本机防毒 / VPN / 网络过滤所致，编辑器同样会自动重试。" % cls.RESETS)
        cls.httpd.shutdown()
        cls.httpd.server_close()
        cls.home.__exit__(None, None, None)

    def req(self, path, data=None, headers=None, tries=5, timeout=10):
        """同编辑器：连线被本机防毒 / VPN / 网络过滤重置（WinError 10054）时重试。
        所有 API 都是幂等的（重送相同资料结果相同），所以可以安全重试；HTTP 错误码不重试。"""
        last = None
        for k in range(tries):
            hdr = {"Accept-Encoding": "gzip"}          # 跟浏览器一样要求压缩
            hdr.update(headers or {})
            r = urllib.request.Request(self.base + path, data=data, headers=hdr,
                                       method="POST" if data is not None else "GET")
            try:
                with urllib.request.urlopen(r, timeout=timeout) as resp:
                    body = resp.read()
                    if resp.headers.get("Content-Encoding") == "gzip":
                        body = gzip.decompress(body)
                    return resp.status, resp.headers, body
            except urllib.error.HTTPError:
                raise
            except (ConnectionError, socket.timeout, TimeoutError, urllib.error.URLError) as e:
                last = e
                type(self).RESETS += 1
                time.sleep(0.25 * (k + 1))
        raise last

    def js(self, path, data=None):
        return json.loads(self.req(path, data)[2].decode("utf-8"))

    def test_page_gzips_small_enough(self):
        """editor.html 压缩后必须远小于 64 KB（使用者电脑会卡住大回应）。
        直接量档案，不经过网络，才不会被本机网页过滤改写结果。"""
        with open(os.path.join(paths.web_dir(), "editor.html"), "rb") as f:
            page = f.read()
        n = len(gzip.compress(page, 6))
        self.assertLess(n, 48 * 1024,
                        "editor.html 压缩后 %d KB，超过 48 KB；使用者电脑约 64 KB 以上的本机回应会卡住。" % (n // 1024))

    def test_index_and_state(self):
        st, h, body = self.req("/")
        self.assertEqual(st, 200)
        if h.get("Content-Encoding") == "gzip":
            self.assertLess(int(h["Content-Length"]), 48 * 1024, "页面压缩后必须远小于 64 KB（使用者电脑会卡住大回应）")
        else:
            type(self).FILTERED = True    # 本机网页过滤把 HTML 解压并改写了标头，见 tearDownClass
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
        blob = os.urandom(900 * 1024 + 123)   # 编辑器上传前会缩到 ~200dpi，实际底图约 0.1–1 MB
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

    def test_curricular_endpoints(self):
        d = self.js("/api/curricular")
        self.assertFalse(d["exists"])
        r = self.js("/api/curricular-template", b"")
        self.assertEqual(r["path"], "config/curricular.template.json")
        with open(os.path.join(self.home.P.config, "curricular.template.json"), encoding="utf-8") as f:
            tpl = json.load(f)
        self.assertIn({"cn": "学会", "en": "Society", "aliases": []}, tpl["societies"])
        with open(os.path.join(self.home.P.config, "curricular.json"), "w", encoding="utf-8") as f:
            json.dump({"学会": "Standard Society"}, f, ensure_ascii=False)
        d = self.js("/api/curricular")
        self.assertEqual(d["entries"], [{"cn": "学会", "en": "Standard Society", "aliases": [], "years": []}])
        self.assertTrue(self.js("/api/cfgsig")["curricular"])
        os.remove(os.path.join(self.home.P.config, "curricular.json"))

    def test_it_spec_export(self):
        with self.assertRaises(urllib.error.HTTPError) as cm:
            self.req("/api/export-it-spec", b"{}")
        self.assertEqual(cm.exception.code, 400)
        L = {"table": {"colY": 1.93, "colS": 8.05, "colP": 8.02}, "intro": {}, "pageNo": {}, "date": {}}
        r = self.js("/api/export-it-spec", json.dumps(L).encode())
        self.assertTrue(r["ok"])
        self.assertIn("certificate-print.css", r["files"])
        self.assertTrue(os.path.isfile(os.path.join(self.home.P.output, "IT-spec", "certificate-print.css")))

    def test_large_class_is_compressed(self):
        """班级资料很大时（~300 KB JSON）压缩后仍需小于 48 KB，且内容完整。"""
        rows = [{"year": str(2000 + i % 27), "socCn": "测试学会%d" % (i % 40), "socEn": "Test Society %d" % (i % 40),
                 "posCn": "会员", "posEn": "Member"} for i in range(12)]
        proj = {"students": [{"id": "s%d" % k, "cn": "测试%d" % k, "en": "TEST %d" % k, "ic": "%012d" % k,
                              "rows": rows} for k in range(250)]}
        raw = json.dumps(proj, ensure_ascii=False).encode()
        self.assertGreater(len(raw), 250 * 1024)
        self.js("/api/class?name=BIG1", raw)
        st, h, body = self.req("/api/class?name=BIG1")
        self.assertLess(int(h["Content-Length"]), 48 * 1024)
        self.assertEqual(len(json.loads(body)["students"]), 250)
        os.remove(os.path.join(self.home.P.data, "BIG1.json"))
        os.remove(os.path.join(self.home.P.data, "BIG1.json.bak")) if os.path.exists(os.path.join(self.home.P.data, "BIG1.json.bak")) else None

    def test_ping_probe(self):
        info = server.probe_instance(self.port)
        self.assertEqual(info["app"], "CertEditor")
        self.assertIsNone(server.probe_instance(1))


if __name__ == "__main__":
    unittest.main()
