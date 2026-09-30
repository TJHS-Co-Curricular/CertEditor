import json
import os
import re
import unittest

from helpers import TempHome

from certeditor import itspec

LAYOUT = {
    "pageW": 21, "pageH": 29.7, "offX": 0.5, "offY": 0.6, "frameH": 28.7, "rowsPerPage": 10,
    "fontFamily": '"Times New Roman", KaiTi, serif',
    "intro": {"show": True, "left": 6.6, "top": 6.6, "width": 12, "size": 12, "lh": 0},
    "table": {"show": True, "left": 1.45, "top": 12.5, "colY": 1.93, "colS": 8, "colP": 8.02, "size": 12,
              "headSize": 12, "rowPad": 0.04, "headMode": "print", "headLine": True, "oneLine": False,
              "headLineDy": 0.15, "headDyY": -0.1, "headDyS": 0, "headDyP": 0.05},
    "pageNo": {"show": False, "left": 1.5, "bottom": 1, "size": 12},
    "date": {"show": True, "left": 13.5, "bottom": 1, "size": 12},
    "tpl": "学生 {cn} (身份证号码: {ic})\nThis is to certify that {en}",
    "headY": "年 YEAR", "headS": "联课团体名称 NAME OF SOCIETIES", "headP": "职位 POSITION",
    "pageTpl": "Page {i} of {n}", "bgImage": "x.jpg",
}


class ItSpecTest(unittest.TestCase):
    def test_css_targets_result_structure_with_values(self):
        css = itspec.build_css(LAYOUT)
        for sel in (".pagebreak > div:nth-of-type(1)", ".pagebreak > div:nth-of-type(2)", ".pagebreak tr.line_btm",
                    '.pagebreak tr[valign="top"]', ".pagebreak > div:nth-of-type(3)", ".pagebreak > div:nth-of-type(4)",
                    ".cert-intro", ".cert-date"):
            self.assertIn(sel, css)
        self.assertIn("@page { size: 21cm 29.7cm; margin: 0; }", css)
        self.assertIn("top: 0.6cm !important", css)                       # offY
        self.assertIn("width: calc(8cm - 2px) !important", css)           # 团体栏宽
        self.assertIn("width: 17.95cm !important", css)                   # 表格总宽
        self.assertIn("padding-bottom: calc(1px + 0.04cm)", css)          # 行距
        self.assertIn("bottom: calc(-2px - 0.15cm);", css)                # 底线上下
        self.assertIn("top: -0.1cm;", css)                                # 表头年份上下
        self.assertIn("calc(-2px - 0.15cm - 0.1cm)", css)
        self.assertNotIn("nth-child(2)::after", css)                      # 团体 dy=0 不产生规则
        page_no = css.split(".pagebreak > div:nth-of-type(3)")[1].split("}")[0]
        self.assertIn("display: none", page_no)                           # 页数不打印
        self.assertEqual(css.count("{"), css.count("}"))

    def test_sample_is_quirks_result_structure_with_synthetic_data(self):
        html = itspec.build_sample(LAYOUT)
        self.assertFalse(html.lstrip().lower().startswith("<!doctype"))
        self.assertEqual(html.count('<div class="pagebreak relative">'), 3)   # 1 页 + 13 行分 2 页
        self.assertIn('<tr class="line_btm">', html)
        self.assertIn('href="certificate-print.css"', html)
        self.assertIn("Page 2 of 2", html)
        self.assertTrue(set(re.findall(r"身份证号码: (\d+)", html)) <= {"000000000001", "000000000002"})

    def test_export_writes_package(self):
        with TempHome() as h:
            P = h.setup()
            with open(os.path.join(P.config, "curricular.json"), "w", encoding="utf-8") as f:
                json.dump({"societies": [{"cn": "测试学会", "en": "Test Society", "years": "2024-2026",
                                          "aliases": ["旧名"]}]}, f, ensure_ascii=False)
            r = itspec.export(LAYOUT)
            self.assertEqual(r["dir"], "output/IT-spec")
            self.assertEqual(r["files"], sorted(["certificate-print.css", "sample.html", "说明-spec.md", "layout.json",
                                                 "curricular.json", "团体名称对照.csv"]))
            d = os.path.join(P.base, "output", "IT-spec")
            with open(os.path.join(d, "团体名称对照.csv"), encoding="utf-8") as f:
                csv_text = f.read()
            self.assertTrue(csv_text.startswith("﻿"))
            self.assertIn("测试学会,Test Society,2024-2026,旧名", csv_text)
            with open(os.path.join(d, "layout.json"), encoding="utf-8") as f:
                self.assertNotIn("bgImage", json.load(f))
            with open(os.path.join(d, "说明-spec.md"), encoding="utf-8") as f:
                spec = f.read()
            self.assertIn("| 栏宽 年份 / 团体 / 职位 | 1.93cm / 8cm / 8.02cm |", spec)


if __name__ == "__main__":
    unittest.main()
