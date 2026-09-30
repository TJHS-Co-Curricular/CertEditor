import json
import os
import unittest

from helpers import TempHome

from certeditor import curricular


class NormalizeTest(unittest.TestCase):
    def test_list_of_objects_wrapped(self):
        e = curricular.normalize({"societies": [
            {"cn": "测试学会", "en": "Test Society", "aliases": ["旧测试学会", "Old Test"]},
            {"中文": "第二学会", "英文": "Second Club", "别名": "二会|2nd Club"},
        ]})
        self.assertEqual(e[0], {"cn": "测试学会", "en": "Test Society", "aliases": ["旧测试学会", "Old Test"], "years": []})
        self.assertEqual(e[1], {"cn": "第二学会", "en": "Second Club", "aliases": ["二会", "2nd Club"], "years": []})

    def test_simple_map_and_comment_keys(self):
        e = curricular.normalize({"_说明": "x", "测试学会": "Test Society"})
        self.assertEqual(e, [{"cn": "测试学会", "en": "Test Society", "aliases": [], "years": []}])

    def test_old_name_to_object(self):
        e = curricular.normalize({"旧名学会": {"cn": "新名学会", "en": "New Society"}})
        self.assertEqual(e, [{"cn": "新名学会", "en": "New Society", "aliases": ["旧名学会"], "years": []}])

    def test_array_rows(self):
        e = curricular.normalize([["测试学会", "Test Society", "别名一", "别名二"], "只有中文"])
        self.assertEqual(e[0]["aliases"], ["别名一", "别名二"])
        self.assertEqual(e[1], {"cn": "只有中文", "en": "", "aliases": [], "years": []})


class YearsTest(unittest.TestCase):
    def test_year_forms(self):
        e = curricular.normalize({"societies": [
            {"cn": "甲", "years": [2025]},
            {"cn": "乙", "year": "2023-2025"},
            {"cn": "丙", "years": "2021, 2023"},
            {"cn": "丁", "from": 2024, "to": 2026},
            {"cn": "戊", "年份": 2026},
            {"cn": "己"},
        ]})
        self.assertEqual([x["years"] for x in e],
                         [[2025], [2023, 2024, 2025], [2021, 2023], [2024, 2025, 2026], [2026], []])

    def test_same_name_different_years(self):
        e = curricular.normalize({"societies": [
            {"cn": "小提琴", "en": "Violin Club", "years": [2025], "aliases": ["弦乐团"]},
            {"cn": "弦乐团", "en": "String Orchestra", "years": [2026], "aliases": ["小提琴"]},
        ]})
        self.assertEqual(len(e), 2)
        self.assertEqual((e[0]["years"], e[1]["years"]), ([2025], [2026]))


class LoadAndTemplateTest(unittest.TestCase):
    def test_missing_bad_and_good_file(self):
        with TempHome() as h:
            P = h.setup()
            d = curricular.load()
            self.assertFalse(d["exists"])
            self.assertEqual(d["path"], "config/curricular.json")
            with open(curricular.path(), "w", encoding="utf-8") as f:
                f.write("{ bad json")
            d = curricular.load()
            self.assertTrue(d["exists"])
            self.assertIn("JSON 格式错误", d["error"])
            with open(curricular.path(), "w", encoding="utf-8-sig") as f:   # 带 BOM 也要能读
                json.dump({"societies": [{"cn": "测试学会", "en": "Test Society"}]}, f, ensure_ascii=False)
            d = curricular.load()
            self.assertEqual(d["error"], "")
            self.assertEqual(len(d["entries"]), 1)
            self.assertTrue(d["sig"])

    def test_template_collects_unique_societies(self):
        with TempHome() as h:
            h.setup()
            projects = [{"students": [
                {"rows": [{"socCn": "乙学会", "socEn": "B Society"}, {"socCn": "甲学会", "socEn": "A Society"}]},
                {"rows": [{"socCn": "乙学会", "socEn": "B Society"}, {"socCn": "", "socEn": ""}]}]}]
            out = curricular.write_template(curricular.collect_societies(projects))
            self.assertTrue(out.endswith("curricular.template.json"))
            self.assertFalse(os.path.exists(curricular.path()), "范本不可覆盖 curricular.json")
            with open(out, encoding="utf-8") as f:
                rows = json.load(f)["societies"]
            self.assertEqual([r["cn"] for r in rows], ["乙学会", "甲学会"] if rows[0]["cn"] == "乙学会" else ["甲学会", "乙学会"])
            self.assertEqual(len(rows), 2)
            # 范本本身也必须是可被读取的格式
            with open(out, encoding="utf-8") as f:
                self.assertEqual(len(curricular.normalize(json.load(f))), 2)


if __name__ == "__main__":
    unittest.main()
