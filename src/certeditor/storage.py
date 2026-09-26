"""班级编辑资料（data/<班级>.json）的读写。"""
import datetime
import json
import os
import re
import shutil

from . import logger, paths
from .parser import parse_result_html

SAFE_NAME = re.compile(r"^[^\\/:*?\"<>|]{1,80}$")
HTML_EXT = (".html", ".htm")


def safe_name(n: str) -> str:
    n = (n or "").strip()
    if not SAFE_NAME.match(n) or n in (".", "..") or n.startswith("."):
        raise ValueError("名称不合法: %r" % n)
    return n


def write_json(path: str, obj) -> None:
    """原子写入，并保留上一版为 .bak。"""
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)
    if os.path.exists(path):
        shutil.copyfile(path, path + ".bak")
    os.replace(tmp, path)


def html_path(name: str):
    for e in HTML_EXT:
        p = os.path.join(paths.P.result, name + e)
        if os.path.exists(p):
            return p
    return None


def data_path(name: str) -> str:
    return os.path.join(paths.P.data, safe_name(name) + ".json")


def list_classes():
    P = paths.P
    names = set()
    for f in os.listdir(P.result):
        if f.lower().endswith(HTML_EXT):
            names.add(os.path.splitext(f)[0])
    for f in os.listdir(P.data):
        if f.lower().endswith(".json"):
            names.add(f[:-5])
    return [{"name": n, "hasHtml": html_path(n) is not None,
             "hasData": os.path.exists(os.path.join(P.data, n + ".json"))} for n in sorted(names)]


def load_class(name: str, force_import: bool = False) -> dict:
    name = safe_name(name)
    dp = data_path(name)
    if os.path.exists(dp) and not force_import:
        with open(dp, "r", encoding="utf-8") as f:
            return json.load(f)
    hp = html_path(name)
    if hp:
        proj = parse_result_html(hp)
        proj["name"] = name
        logger.log("导入 %s -> %d 位学生" % (os.path.basename(hp), len(proj["students"])))
        return proj
    return {"name": name, "date": datetime.date.today().isoformat(), "dateText": "", "students": []}


def save_class(name: str, data: dict) -> str:
    name = safe_name(name)
    data["name"] = name
    data["savedAt"] = datetime.datetime.now().isoformat(timespec="seconds")
    write_json(data_path(name), data)
    logger.log("已保存 %s (%d 位学生)" % (name, len(data.get("students", []))))
    return data["savedAt"]


def delete_class_data(name: str) -> None:
    p = data_path(name)
    if os.path.exists(p):
        shutil.move(p, p + ".deleted")
    logger.log("已删除编辑资料 " + name)
