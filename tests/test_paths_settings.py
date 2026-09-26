import json
import os
import unittest

from helpers import TempHome

from certeditor import paths, settings
from certeditor.server import client_allowed


def touch(p, data=b"x"):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "wb") as f:
        f.write(data)


class MigrationTest(unittest.TestCase):
    def test_old_layout_is_migrated(self):
        with TempHome() as h:
            b = h.dir
            touch(os.path.join(b, "CertEditor_Data", "S3C1.json"), b"{}")
            touch(os.path.join(b, "CertEditor_Data", "settings.json"), b"{}")
            touch(os.path.join(b, "CertEditor_Data", "background.jpg"), b"img")
            touch(os.path.join(b, "Output", "S3C1_print.html"), b"<html>")
            touch(os.path.join(b, "CertEditor_Portable.ini"), b"[Server]\nPort = 9000\n")
            msgs = paths.migrate(h.P)
            h.P.ensure()
            names = os.listdir(b)
            self.assertIn("data", names)
            self.assertIn("output", names)
            self.assertNotIn("CertEditor_Data", names)
            self.assertNotIn("Output", names)
            self.assertTrue(os.path.isfile(os.path.join(b, "data", "S3C1.json")))
            self.assertTrue(os.path.isfile(os.path.join(b, "output", "S3C1_print.html")))
            self.assertTrue(os.path.isfile(os.path.join(b, "config", "settings.json")))
            self.assertTrue(os.path.isfile(os.path.join(b, "config", "background.jpg")))
            self.assertTrue(os.path.isfile(os.path.join(b, "config", "CertEditor.ini")))
            self.assertFalse(os.path.exists(os.path.join(b, "CertEditor_Portable.ini")))
            self.assertTrue(msgs)
            # 再执行一次不应出错、不应有动作
            self.assertEqual(paths.migrate(h.P), [])


class SettingsTest(unittest.TestCase):
    def test_default_ini_created_and_parsed(self):
        with TempHome() as h:
            h.setup()
            cfg = settings.load_ini()
            self.assertTrue(os.path.isfile(h.P.ini))
            self.assertEqual((cfg.lan, cfg.port, cfg.autoport, cfg.browser, cfg.allow), (False, 8765, True, True, []))

    def test_ini_values(self):
        with TempHome() as h:
            h.setup()
            with open(h.P.ini, "w", encoding="utf-8-sig") as f:
                f.write("[Server]\nLanAccess = true ; 注解\nPort = 9100\nAutoPort = false\n"
                        "OpenBrowser = no\nAllowIPs = 192.168.1.0/24, 10.0.0.5, bad\n")
            cfg = settings.load_ini()
            self.assertEqual((cfg.lan, cfg.port, cfg.autoport, cfg.browser), (True, 9100, False, False))
            self.assertEqual([str(n) for n in cfg.allow], ["192.168.1.0/24", "10.0.0.5/32"])
            self.assertTrue(client_allowed("127.0.0.1", cfg))
            self.assertTrue(client_allowed("192.168.1.77", cfg))
            self.assertFalse(client_allowed("192.168.2.1", cfg))
            cfg.lan = False
            self.assertFalse(client_allowed("192.168.1.77", cfg))

    def test_resolve_background(self):
        with TempHome() as h:
            P = h.setup()
            self.assertIsNone(settings.resolve_bg({}))
            touch(os.path.join(P.config, "background.jpg"))
            self.assertTrue(settings.resolve_bg({}).endswith(os.path.join("config", "background.jpg")))
            touch(os.path.join(P.base, "Example.png"))
            self.assertTrue(settings.resolve_bg({"bgImage": "Example.png"}).endswith("Example.png"))
            # 找不到时退回 config/background.*，cfg_sig 标示 missing
            with open(P.settings, "w", encoding="utf-8") as f:
                json.dump({"bgImage": "nope.jpg"}, f)
            sig = settings.cfg_sig()
            self.assertEqual(sig["bgMissing"], "nope.jpg")
            self.assertEqual(sig["bgPath"], "config/background.jpg")


if __name__ == "__main__":
    unittest.main()
