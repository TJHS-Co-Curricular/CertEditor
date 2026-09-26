import os
import unittest

from helpers import TempHome, make_result_html

from certeditor.parser import parse_date, parse_result_html

STUDENTS = [
    ("测试甲", "080101010001", "TEST ONE",
     [("2021", "华语口才培训队", "Chinese Eloquence Team", "会员", "Member"),
      ("2022", "乒乓培训队", "School Table-Tennis Team", "副秘书", "Vice Head of Secretary")]),
    ("测试乙", "080101010002", "TEST TWO",
     [(str(2014 + i), "学会%d" % i, "Society %d" % i, "会员", "Member") for i in range(13)]),
]


class ParserTest(unittest.TestCase):
    def test_parse_gbk_file(self):
        with TempHome() as h:
            P = h.setup()
            p = os.path.join(P.result, "S9X9.html")
            with open(p, "wb") as f:
                f.write(make_result_html(STUDENTS))
            proj = parse_result_html(p)
        self.assertEqual(proj["name"], "S9X9")
        self.assertEqual(proj["date"], "2026-11-21")
        self.assertEqual(len(proj["students"]), 2, "多页学生应合并成一位")
        a, b = proj["students"]
        self.assertEqual((a["cn"], a["ic"], a["en"]), ("测试甲", "080101010001", "TEST ONE"))
        self.assertEqual(a["rows"][1], {"year": "2022", "socCn": "乒乓培训队", "socEn": "School Table-Tennis Team",
                                        "posCn": "副秘书", "posEn": "Vice Head of Secretary"})
        self.assertEqual(len(b["rows"]), 13)
        self.assertEqual(b["rows"][-1]["year"], "2026")
        self.assertTrue(all(s["id"] for s in proj["students"]))
        self.assertNotEqual(a["id"], b["id"])

    def test_parse_date(self):
        self.assertEqual(parse_date("21<sup>st</sup> November 2026"), "2026-11-21")
        self.assertEqual(parse_date("2nd March 2025"), "2025-03-02")
        self.assertEqual(parse_date("nonsense"), "")


if __name__ == "__main__":
    unittest.main()
