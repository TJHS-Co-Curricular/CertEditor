"""团体名称映射：config/curricular.json。

打印 / 预览时，把学生资料里的团体名称（中文或英文，或任何别名）对应到 curricular.json 的标准中文 / 英文名称。
学生资料本身不修改。

支持的格式（任选一种）::

    # 1) 推荐：物件列表（可包在 {"societies": [...]} 里）
    {"societies": [
        {"cn": "华语学会", "en": "Chinese Language Society", "aliases": ["华文学会", "Chinese Society"]}
    ]}

    # 2) 中文 → 英文 对照
    {"华语学会": "Chinese Language Society"}

    # 3) 旧名称 → 新名称物件（键会当作别名）
    {"华文学会": {"cn": "华语学会", "en": "Chinese Language Society"}}

    # 4) 阵列列表 [中文, 英文, 别名...]
    [["华语学会", "Chinese Language Society", "华文学会"]]

年份限定（同一个名称在不同年份印成不同名称）::

    {"societies": [
        {"cn": "小提琴",   "en": "Violin Club",     "years": [2025],        "aliases": ["弦乐团"]},
        {"cn": "弦乐团",   "en": "String Orchestra", "years": "2026-2030",  "aliases": ["小提琴"]}
    ]}

    years 可写 2025、"2025"、[2024, 2025]、"2023-2025"、"2023,2025"，或用 from / to。
    有写年份的项目只套用在那些年份的行；同名称没有符合年份的项目时，才用没写年份的项目。

栏位名称也接受：zh / chinese / name_cn / 中文 / 名称 / name；english / name_en / 英文；
alias / match / old / 别名 / 旧名（字串可用 | ; 、 , 分隔）。
"""
import json
import os
import re
from typing import List

from . import logger, paths
from .settings import file_sig
from .storage import write_json

FILE_NAME = "curricular.json"
TEMPLATE_NAME = "curricular.template.json"

CN_KEYS = ("cn", "zh", "chinese", "name_cn", "nameCn", "cn_name", "中文", "中文名", "中文名称", "名称", "name")
EN_KEYS = ("en", "english", "name_en", "nameEn", "en_name", "英文", "英文名", "英文名称")
ALIAS_KEYS = ("aliases", "alias", "match", "matches", "old", "old_names", "别名", "旧名")
WRAP_KEYS = ("societies", "curricular", "clubs", "items", "data", "list", "团体", "学会")


def path() -> str:
    return os.path.join(paths.P.config, FILE_NAME)


def _pick(d: dict, keys) -> str:
    for k in keys:
        v = d.get(k)
        if isinstance(v, (str, int, float)) and str(v).strip():
            return str(v).strip()
    return ""


def _aliases(v) -> List[str]:
    if v is None:
        return []
    if isinstance(v, str):
        v = re.split(r"[|;；、,，\n]+", v)
    if isinstance(v, (list, tuple)):
        return [str(x).strip() for x in v if str(x).strip()]
    return []


YEAR_KEYS = ("years", "year", "年份", "年")


def _years(d: dict) -> List[int]:
    """把 years / year / from-to 转成排序后的年份列表；空列表 = 不限年份。"""
    ys = set()

    def add(v):
        if isinstance(v, bool) or v is None:
            return
        if isinstance(v, (int, float)):
            ys.add(int(v))
        elif isinstance(v, (list, tuple)):
            for x in v:
                add(x)
        elif isinstance(v, str):
            for part in re.split(r"[,，;；、\s]+", v.strip()):
                m = re.fullmatch(r"(\d{4})\s*[-–~至到]\s*(\d{4})", part)
                if m:
                    a, b = sorted((int(m.group(1)), int(m.group(2))))
                    ys.update(range(a, b + 1))
                elif re.fullmatch(r"\d{4}", part):
                    ys.add(int(part))

    for k in YEAR_KEYS:
        add(d.get(k))
    f, t = d.get("from"), d.get("to")
    if f or t:
        try:
            a = int(f) if f else int(t)
            b = int(t) if t else a + 50
            ys.update(range(min(a, b), max(a, b) + 1))
        except (TypeError, ValueError):
            pass
    return sorted(ys)


def _entry(d: dict) -> dict:
    al: List[str] = []
    for k in ALIAS_KEYS:
        al += _aliases(d.get(k))
    return {"cn": _pick(d, CN_KEYS), "en": _pick(d, EN_KEYS), "aliases": al, "years": _years(d)}


def normalize(raw) -> List[dict]:
    items: List[dict] = []
    if isinstance(raw, dict):
        for k in WRAP_KEYS:
            if isinstance(raw.get(k), (list, dict)):
                return normalize(raw[k])
        for k, v in raw.items():
            if str(k).startswith("_"):          # _comment 等说明栏位
                continue
            if isinstance(v, str):
                items.append({"cn": str(k).strip(), "en": v.strip(), "aliases": [], "years": []})
            elif isinstance(v, dict):
                e = _entry(v)
                if not e["cn"] and not e["en"]:
                    e["cn"] = str(k).strip()
                elif str(k).strip() not in (e["cn"], e["en"]):
                    e["aliases"].append(str(k).strip())
                items.append(e)
    elif isinstance(raw, list):
        for v in raw:
            if isinstance(v, dict):
                items.append(_entry(v))
            elif isinstance(v, (list, tuple)) and v:
                s = [str(x).strip() for x in v]
                items.append({"cn": s[0], "en": s[1] if len(s) > 1 else "", "aliases": [x for x in s[2:] if x], "years": []})
            elif isinstance(v, str) and v.strip():
                items.append({"cn": v.strip(), "en": "", "aliases": [], "years": []})
    return [e for e in items if e["cn"] or e["en"]]


def load() -> dict:
    """回传 {"exists", "path", "sig", "entries", "error"}。"""
    p = path()
    out = {"exists": os.path.isfile(p), "path": os.path.relpath(p, paths.P.base).replace("\\", "/"),
           "sig": file_sig(p), "entries": [], "error": ""}
    if not out["exists"]:
        return out
    try:
        with open(p, "r", encoding="utf-8-sig") as f:
            out["entries"] = normalize(json.load(f))
        if not out["entries"]:
            out["error"] = "文件里没有可用的团体名称（请检查格式）"
    except json.JSONDecodeError as e:
        out["error"] = "JSON 格式错误：第 %d 行第 %d 字（%s）" % (e.lineno, e.colno, e.msg)
    except Exception as e:  # noqa: BLE001
        out["error"] = str(e)
    if out["error"]:
        logger.log("curricular.json 读取失败：" + out["error"])
    return out


def write_template(societies: List[dict]) -> str:
    """把目前所有班级出现过的团体名称写成 config/curricular.template.json（不会覆盖 curricular.json）。"""
    seen, rows = set(), []
    for s in societies:
        key = (s.get("cn", "").strip(), s.get("en", "").strip())
        if key in seen or not any(key):
            continue
        seen.add(key)
        rows.append({"cn": key[0], "en": key[1], "aliases": []})
    rows.sort(key=lambda r: (r["cn"], r["en"]))
    out = os.path.join(paths.P.config, TEMPLATE_NAME)
    write_json(out, {"_说明": "改好后另存为 curricular.json；aliases 填其他写法（旧名、错字、简称）也会对应到这一项。",
                     "societies": rows})
    logger.log("已产生范本 %s（%d 个团体）" % (os.path.relpath(out, paths.P.base), len(rows)))
    return out


def collect_societies(projects) -> List[dict]:
    out = []
    for proj in projects:
        for st in proj.get("students", []):
            for r in st.get("rows", []):
                if r.get("socCn") or r.get("socEn"):
                    out.append({"cn": r.get("socCn", ""), "en": r.get("socEn", "")})
    return out


def sig() -> str:
    return file_sig(path())
