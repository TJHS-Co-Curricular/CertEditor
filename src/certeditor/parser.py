"""解析学校系统导出的 Result/*.html（GBK / UTF-8，每位学生一页或多页）。"""
import datetime
import html
import os
import re
import uuid

__all__ = ["read_html_text", "parse_result_html", "parse_date"]


def read_html_text(path):
    with open(path, "rb") as f:
        raw = f.read()
    m = re.search(rb'charset=["\']?([A-Za-z0-9_\-]+)', raw[:3000])
    encs = []
    if m:
        e = m.group(1).decode("ascii", "ignore").lower()
        encs.append("gb18030" if e in ("gbk", "gb2312", "gb18030") else e)
    encs += ["utf-8", "gb18030"]
    for e in encs:
        try:
            return raw.decode(e)
        except Exception:
            continue
    return raw.decode("gb18030", errors="replace")


def strip_tags(s):
    return html.unescape(re.sub(r"<[^>]+>", "", s)).strip()


def split_br(cell):
    parts = [strip_tags(p) for p in re.split(r"<br\s*/?>", cell, flags=re.I)]
    cn = parts[0] if parts else ""
    en = " ".join(p for p in parts[1:] if p)
    return cn, en


MONTHS = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july",
     "august", "september", "october", "november", "december"], 1)}


def parse_date(text):
    t = strip_tags(text)
    m = re.search(r"(\d{1,2})\s*(?:st|nd|rd|th)?\s+([A-Za-z]+)\s+(\d{4})", t)
    if m and m.group(2).lower() in MONTHS:
        try:
            return datetime.date(int(m.group(3)), MONTHS[m.group(2).lower()], int(m.group(1))).isoformat()
        except ValueError:
            pass
    return ""


def parse_result_html(path):
    text = read_html_text(path)
    pages = re.split(r'<div class="pagebreak[^"]*">', text)[1:]
    students = []
    date_iso = ""
    for p in pages:
        intro_m = re.search(r'<div class="absolute"[^>]*>(.*?)</div>', p, re.S)
        intro = intro_m.group(1) if intro_m else ""
        lines = [strip_tags(x) for x in re.split(r"<br\s*/?>", intro, flags=re.I)]
        cn = ic = en = ""
        for ln in lines:
            m = re.search(r"学生\s*(.*?)\s*[（(]\s*身份证号码[:：]\s*([^)）]*)[)）]", ln)
            if m:
                cn, ic = m.group(1).strip(), m.group(2).strip()
            m = re.search(r"certify that\s+(.*)$", ln, re.I)
            if m:
                en = m.group(1).strip()
        rows = []
        for r in re.findall(r'<tr valign="top"[^>]*>(.*?)</tr>', p, re.S):
            tds = re.findall(r"<td[^>]*>(.*?)</td>", r, re.S)
            if len(tds) < 3:
                continue
            sc, se = split_br(tds[1])
            pc, pe = split_br(tds[2])
            rows.append({"year": strip_tags(tds[0]), "socCn": sc, "socEn": se, "posCn": pc, "posEn": pe})
        m = re.search(r"<!--\s*日期\s*-->\s*<div[^>]*>(.*?)</div>", p, re.S)
        if m and not date_iso:
            date_iso = parse_date(m.group(1))
        prev = students[-1] if students else None
        pm = re.search(r"Page\s+(\d+)\s+of\s+(\d+)", p)
        is_cont = pm and int(pm.group(1)) > 1
        if prev and is_cont and prev["ic"] == ic and prev["cn"] == cn:
            prev["rows"].extend(rows)
        else:
            students.append({"cn": cn, "ic": ic, "en": en, "rows": rows})
    for s in students:
        s["id"] = "s" + uuid.uuid4().hex[:12]
    return {"name": os.path.splitext(os.path.basename(path))[0], "date": date_iso,
            "dateText": "", "source": os.path.basename(path), "students": students,
            "importedAt": datetime.datetime.now().isoformat(timespec="seconds")}
