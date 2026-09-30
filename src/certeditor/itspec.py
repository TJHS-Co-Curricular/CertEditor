"""导出给学校系统 IT 的版面规格包（output/IT-spec/）。

依照 Result HTML（学校系统 activity 列印页）的 DOM 结构产生可直接套用的 CSS，
让对方不必改 HTML 结构，只要在原本的 <style> 之后加一行 <link> 就能印出与本编辑器相同的位置。

Result 每页的结构（不变）::

    <div class="pagebreak relative">
      <div class="absolute" …>证明文字…</div>                 ← 第 1 个 div：证明文字
      <div class="absolute" …><table border=0 cellspacing=0>  ← 第 2 个 div：表格
          <tr class="line_btm"><td>年 YEAR</td>…</tr>          ← 表头
          <tr valign="top" style="font-size:12pt;">…</tr>      ← 每一行
      </table></div>
      <div class="center absolute" …>Page 1 of 1</div>         ← 第 3 个 div：页数
      <div class="center absolute" …>21<sup>st</sup> …</div>   ← 第 4 个 div：日期
    </div>
"""
import csv
import datetime
import html
import io
import json
import os
from typing import Dict, List

from . import __version__, curricular, logger, paths

OUT_DIRNAME = "IT-spec"


def _n(v, d=0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return d


def _cm(v) -> str:
    x = round(_n(v), 3)
    return ("%g" % x) + "cm"


def _pt(v) -> str:
    return ("%g" % round(_n(v, 12), 2)) + "pt"


# ---------------------------------------------------------------------- CSS
def build_css(L: dict) -> str:
    T = L.get("table", {})
    intro, pno, date = L.get("intro", {}), L.get("pageNo", {}), L.get("date", {})
    colY, colS, colP = _n(T.get("colY"), 1.93), _n(T.get("colS"), 8.05), _n(T.get("colP"), 8.02)
    tw = colY + colS + colP
    pageW, pageH = _n(L.get("pageW"), 21), _n(L.get("pageH"), 29.7)
    offX, offY, frameH = _n(L.get("offX"), 0.5), _n(L.get("offY"), 0.5), _n(L.get("frameH"), 28.7)
    pad = max(0.0, _n(T.get("rowPad")))
    hl = _n(T.get("headLineDy"))
    dys = [_n(T.get("headDyY")), _n(T.get("headDyS")), _n(T.get("headDyP"))]
    head_mode = T.get("headMode", "print")
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    P = ".pagebreak"          # 原系统 class
    out: List[str] = []
    w = out.append
    w("""/* ==========================================================================
   联课证书 列印版面 CSS — 由 CertEditor v%s 于 %s 依目前校准值产生
   --------------------------------------------------------------------------
   用法（二选一）：
   A. 不改 HTML：在列印页原本的 <style> 之后加入
        <link rel="stylesheet" href="certificate-print.css">
      选择器直接对应原本结构（.pagebreak 里第 1~4 个 div、tr.line_btm、tr[valign=top]）。
   B. 改用语意 class：同一组规则也适用 .cert-intro / .cert-table-box / .cert-page-no / .cert-date 等。
   注意：页面须维持「无 DOCTYPE」(quirks 模式)，否则行高会与原本不同。
   单位：cm / pt；打印：纸张 %s×%s cm、缩放 100%%、不要页首页尾。
   ========================================================================== */
""" % (__version__, now, _cm(pageW)[:-2], _cm(pageH)[:-2]))

    w("""/* 1. 纸张与版心 ----------------------------------------------------------- */
@page { size: %s %s; margin: 0; }
body { margin: 0; }
%s, .cert-page {
  position: relative !important;
  left: %s !important;              /* 整体偏移 X（打印机校准） */
  top: %s !important;               /* 整体偏移 Y */
  width: %s !important;
  height: %s !important;            /* 版心高度；页数 / 日期以此底部为基准 */
  font-family: %s !important;
  page-break-after: always; break-after: page;
  box-sizing: border-box;
}
%s:last-of-type, .cert-page:last-of-type { page-break-after: auto; break-after: auto; }
""" % (_cm(pageW), _cm(pageH), P, _cm(offX), _cm(offY), _cm(pageW - offX), _cm(frameH),
       L.get("fontFamily") or '"Times New Roman", KaiTi, serif', P))

    lh = ("  line-height: %g !important;\n" % _n(intro.get("lh"))) if _n(intro.get("lh")) > 0 else ""
    w("""/* 2. 证明文字（学生 XXX (身份证号码…) … This is to certify that …） ----------- */
%s > div:nth-of-type(1), .cert-intro {
  position: absolute !important;
  left: %s !important;
  top: %s !important;
  width: %s !important;
  font-size: %s !important;
%s%s}
""" % (P, _cm(intro.get("left", 6.6)), _cm(intro.get("top", 6.6)), _cm(intro.get("width", 12)),
       _pt(intro.get("size", 12)), lh, "" if intro.get("show", True) else "  display: none !important;\n"))

    w("""/* 3. 联课表格 ------------------------------------------------------------- */
%s > div:nth-of-type(2), .cert-table-box {
  position: absolute !important;
  left: %s !important;
  top: %s !important;
  width: %s !important;
%s}
%s > div:nth-of-type(2) > table, .cert-table {
  table-layout: fixed !important;
  width: %s !important;
  border-collapse: separate !important;
  border-spacing: 0 !important;
}
%s > div:nth-of-type(2) td, .cert-table td { padding: 1px; vertical-align: top; overflow-wrap: anywhere; }
/* 栏宽：年份 / 团体 / 职位（覆盖原本 td 上的 2cm / 9cm / 9cm）；td 的 width 不含左右 1px padding，所以减 2px */
%s > div:nth-of-type(2) tr > td:nth-child(1), .cert-table td:nth-child(1) { width: calc(%s - 2px) !important; }
%s > div:nth-of-type(2) tr > td:nth-child(2), .cert-table td:nth-child(2) { width: calc(%s - 2px) !important; }
%s > div:nth-of-type(2) tr > td:nth-child(3), .cert-table td:nth-child(3) { width: calc(%s - 2px) !important; }
/* 内容行 */
%s tr[valign="top"], .cert-row { font-size: %s !important; }
""" % (P, _cm(T.get("left", 1)), _cm(T.get("top", 12.5)), _cm(tw),
       "" if T.get("show", True) else "  display: none !important;\n",
       P, _cm(tw), P, P, _cm(colY), P, _cm(colS), P, _cm(colP), P, _pt(T.get("size", 12))))
    if pad > 0:
        w('%s tr[valign="top"] > td, .cert-row > td { padding-bottom: calc(1px + %s) !important; }  /* 行距 */\n'
          % (P, _cm(pad)))
    if T.get("oneLine"):
        w("/* 注：「团体/职位中英同一行」无法只用 CSS 做到，请在 HTML 把中英之间的 <br> 改成空格。 */\n")

    # header
    head_vis = {"blank": "  visibility: hidden !important;   /* 不打印但保留位置 */\n",
                "none": "  display: none !important;         /* 不打印也不留位置 */\n"}.get(head_mode, "")
    w("""/* 4. 表头（年 YEAR / 联课团体名称 / 职位）与底线 ---------------------------- */
%s tr.line_btm, .cert-head {
  font-size: %s !important;
%s}
%s tr.line_btm > td, .cert-head > td { vertical-align: bottom; position: relative; }
""" % (P, _pt(T.get("headSize", 12)), head_vis, P))
    if T.get("headLine", True):
        w("""/* 底线用 ::after 画（跟文字分开，可单独上下调整）；原本的 border 改透明但保留 2px 空间 */
%s tr.line_btm > td, .cert-head > td { border-bottom: 2px solid transparent !important; }
%s tr.line_btm > td::after, .cert-head > td::after {
  content: ""; position: absolute; left: 0; right: 0; border-top: 2px solid #000;
  bottom: calc(-2px - %s);           /* 底线上下：正数往下 */
}
""" % (P, P, _cm(hl)))
    else:
        w("%s tr.line_btm > td, .cert-head > td { border-bottom: 0 !important; }\n" % P)
    names = ("年份", "团体", "职位")
    for i, dy in enumerate(dys, 1):
        if dy:
            w("""%s tr.line_btm > td:nth-child(%d), .cert-head > td:nth-child(%d) { top: %s; }   /* 表头「%s」上下 */
%s tr.line_btm > td:nth-child(%d)::after, .cert-head > td:nth-child(%d)::after { bottom: calc(-2px - %s %s %s); }  /* 底线不跟着动 */
""" % (P, i, i, _cm(dy), names[i - 1], P, i, i, _cm(hl), "+" if dy >= 0 else "-", _cm(abs(dy))))

    def foot(n, cls, d, label):
        return """%s > div:nth-of-type(%d), .%s {
  position: absolute !important;
  left: %s !important;
  bottom: %s !important;            /* 离版心底部 */
  top: auto !important;
  font-size: %s !important;
%s}
""" % (P, n, cls, _cm(d.get("left")), _cm(d.get("bottom", 1)), _pt(d.get("size", 12)),
       "" if d.get("show", True) else "  display: none !important;   /* %s 不打印 */\n" % label)

    w("/* 5. 页数（Page 1 of 1）与日期 ------------------------------------------- */\n")
    w(foot(3, "cert-page-no", pno, "页数"))
    w(foot(4, "cert-date", date, "日期"))
    w("""
/* 6. 屏幕预览（不影响打印）：模拟整张纸，方便对照 -------------------------- */
@media screen {
  body { background: #888; padding: 10px 0; }
  %s, .cert-page { background: #fff; outline: %s solid #fff; box-shadow: 0 2px 12px rgba(0,0,0,.45);
    margin-bottom: 1.2cm; }
}
""" % (P, _cm(0.5)))
    return "".join(out)


# ---------------------------------------------------------------------- sample HTML
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September",
          "October", "November", "December"]


def _date_html(d: datetime.date) -> str:
    day = d.day
    suf = "th" if 11 <= day % 100 <= 13 else {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
    return "%d<sup>%s</sup> %s %d" % (day, suf, MONTHS[d.month - 1], d.year)


def _page(L: dict, cn, ic, en, rows, i, n, date_html) -> str:
    e = html.escape
    intro = "<br>".join(e(x).replace("{cn}", e(cn)).replace("{en}", e(en)).replace("{ic}", e(ic))
                        for x in (L.get("tpl") or "").split("\n"))
    trs = "".join("""<tr valign="top" style="font-size:12pt;">
								<td>%s</td>
								<td>%s<br>%s</td>
								<td>%s<br>%s</td>
							</tr>""" % tuple(e(x) for x in r) for r in rows)
    pt = e(L.get("pageTpl") or "Page {i} of {n}").replace("{i}", str(i)).replace("{n}", str(n))
    return """<div class="pagebreak relative">
	<div class="absolute" style="width:12cm;top: 6.6cm;left: 6.6cm;font-size:12pt;">
	%s	</div>

	<div class="absolute" style="top: 12.5cm;left: 1cm;table-layout: fixed;width: 18cm;">
		<table border="0" cellspacing="0">
			<tbody><tr class="line_btm">
				<td style="width: 2cm;">%s</td>
				<td style="width: 9cm;">%s</td>
				<td style="width: 9cm;">%s</td>
			</tr>
			%s		</tbody></table>
	</div>

	<!-- 页数 -->
	<div class="center absolute" style="left: 1.5cm;bottom: 1.0cm;">
		%s	</div>

	<!-- 日期 -->
	<div class="center absolute" style="left: 10.5cm;bottom: 1.0cm;">
		%s	</div>
</div>""" % (intro, e(L.get("headY", "")), e(L.get("headS", "")), e(L.get("headP", "")), trs, pt, date_html)


SAMPLE_STUDENTS = [
    ("测试甲", "000000000001", "TEST STUDENT ONE",
     [("2024", "测试学会", "Test Society", "会员", "Member"),
      ("2025", "测试学会", "Test Society", "秘书", "Secretary"),
      ("2026", "示范培训队", "Demo Training Team", "副主席", "Vice President")]),
    ("测试乙", "000000000002", "TEST STUDENT TWO",
     [(str(2014 + k), "示范学会%d" % k, "Demo Society %d" % k, "会员", "Member") for k in range(13)]),
]


def build_sample(L: dict) -> str:
    """与 Result 相同结构（无 DOCTYPE、相同 class 与 inline style），只放合成资料。"""
    per = max(1, int(round(_n(L.get("rowsPerPage"), 10))))
    d = _date_html(datetime.date(2026, 11, 21))
    pages = []
    for cn, ic, en, rows in SAMPLE_STUDENTS:
        chunks = [rows[i:i + per] for i in range(0, len(rows), per)] or [[]]
        for i, ch in enumerate(chunks, 1):
            pages.append(_page(L, cn, ic, en, ch, i, len(chunks), d))
    # 原系统每页前都有同样的 <style>；这里保留一份，示范 CSS 覆盖得了它
    return """<html><head><meta http-equiv="Content-Type" content="text/html; charset=utf-8">
<title>联课证书 列印范例（合成资料）</title>
<style type="text/css">
@media print{ @page { margin: 0.5cm; } }
body{ margin: 0; font-family: Kaiti,Arial; }
div{ box-sizing: border-box; }
.relative{ position: relative; } .absolute{ position: absolute; } .center{ text-align: center; }
.pagebreak{ page-break-after: always; width: 20cm; height: 28.7cm; font-family: "Times New Roman",Kaiti; }
.line_btm td{ border-bottom: 2px solid black; }
</style>
<!-- ↓ 学校系统只要加这一行（放在原本 <style> 之后） -->
<link rel="stylesheet" href="certificate-print.css">
</head>
<body>
%s
</body></html>
""" % "\n".join(pages)


# ---------------------------------------------------------------------- spec
def build_spec(L: dict, cur: dict) -> str:
    T, intro, pno, date = L.get("table", {}), L.get("intro", {}), L.get("pageNo", {}), L.get("date", {})
    rows = [
        ("纸张", "%s × %s" % (_cm(L.get("pageW", 21)), _cm(L.get("pageH", 29.7))), "@page size；打印边距 0"),
        ("整体偏移 X / Y", "%s / %s" % (_cm(L.get("offX", .5)), _cm(L.get("offY", .5))), ".pagebreak 相对位移（原系统用 @page margin 0.5cm）"),
        ("版心", "%s × %s" % (_cm(_n(L.get("pageW"), 21) - _n(L.get("offX"), .5)), _cm(L.get("frameH", 28.7))), "页数 / 日期的 bottom 以此为基准"),
        ("字体", L.get("fontFamily", ""), ""),
        ("每页行数", str(L.get("rowsPerPage", 10)), "超过自动分页，页数「%s」" % L.get("pageTpl", "")),
        ("证明文字 left / top / width", "%s / %s / %s" % (_cm(intro.get("left")), _cm(intro.get("top")), _cm(intro.get("width"))),
         "字号 %s%s" % (_pt(intro.get("size")), "" if intro.get("show", True) else "（不打印）")),
        ("表格 left / top", "%s / %s" % (_cm(T.get("left")), _cm(T.get("top"))), "" if T.get("show", True) else "（不打印）"),
        ("栏宽 年份 / 团体 / 职位", "%s / %s / %s" % (_cm(T.get("colY")), _cm(T.get("colS")), _cm(T.get("colP"))),
         "table-layout: fixed；原本 2/9/9cm 被 18cm 容器压缩后实际约 1.93/8.05/8.02"),
        ("内容字号 / 行距", "%s / %s" % (_pt(T.get("size")), _cm(T.get("rowPad"))), "行距 = 每行额外底部空间"),
        ("表头字号 / 模式", "%s / %s" % (_pt(T.get("headSize")), {"print": "打印", "blank": "不打印（保留位置）", "none": "不打印（不留位置）"}.get(T.get("headMode", "print"))), ""),
        ("表头底线", ("2px，上下 %s" % _cm(T.get("headLineDy"))) if T.get("headLine", True) else "无", ""),
        ("表头文字上下 年份 / 团体 / 职位", "%s / %s / %s" % (_cm(T.get("headDyY")), _cm(T.get("headDyS")), _cm(T.get("headDyP"))), "正数往下"),
        ("页数 left / bottom", "%s / %s" % (_cm(pno.get("left")), _cm(pno.get("bottom"))), "字号 %s%s" % (_pt(pno.get("size")), "" if pno.get("show", True) else "（不打印）")),
        ("日期 left / bottom", "%s / %s" % (_cm(date.get("left")), _cm(date.get("bottom"))), "字号 %s%s" % (_pt(date.get("size")), "" if date.get("show", True) else "（不打印）")),
    ]
    tbl = "\n".join("| %s | %s | %s |" % (a, b.replace("|", "\\|"), c) for a, b, c in rows)
    tpl = (L.get("tpl") or "").replace("\n", "\n    ")
    ent = cur.get("entries") or []
    return """# 联课证书 列印版面规格（给学校系统 IT）

由 CertEditor v{ver} 于 {now} 依目前「版面 & 纸张校准」产生。数值已在实际证书纸上校准过。

## 包内文件
| 文件 | 用途 |
|---|---|
| `certificate-print.css` | 直接套用的 CSS（选择器对应现有列印页结构，不必改 HTML） |
| `sample.html` | 与现有列印页**相同结构**的范例（合成资料），已连结上面的 CSS，可直接用浏览器打开 / 打印对照 |
| `layout.json` | 全部版面数值（机器可读） |
| `curricular.json`、`团体名称对照.csv` | 团体名称标准化对照（若有设定） |

## 套用方式
1. 在现有列印页（每页 `<div class="pagebreak relative">`）的 `<head>`，**原本 `<style>` 之后**加入：
   `<link rel="stylesheet" href="certificate-print.css">`
2. 维持**没有 `<!DOCTYPE>`**（quirks 模式）；加上 DOCTYPE 会改变行高，位置会偏。
3. 打印：纸张 {pw} × {ph} cm、缩放 100%、不要页首 / 页尾（CSS 已设 `@page margin: 0`）。
4. 若日后愿意改 HTML，可改用语意 class：`.cert-page`、`.cert-intro`、`.cert-table-box`、`.cert-table`、
   `.cert-head`、`.cert-row`、`.cert-page-no`、`.cert-date`（CSS 已同时支援），就不必依赖第几个 div。

## 结构对照
| 现有结构 | 语意 class | 内容 |
|---|---|---|
| `.pagebreak` | `.cert-page` | 每页（每位学生可多页） |
| `.pagebreak > div:nth-of-type(1)` | `.cert-intro` | 证明文字 |
| `.pagebreak > div:nth-of-type(2)` | `.cert-table-box` | 表格容器 |
| `… > table` | `.cert-table` | 表格 |
| `tr.line_btm` | `.cert-head` | 表头 + 底线 |
| `tr[valign="top"]` | `.cert-row` | 每一行（年份 / 团体中英 / 职位中英） |
| `.pagebreak > div:nth-of-type(3)` | `.cert-page-no` | 页数 |
| `.pagebreak > div:nth-of-type(4)` | `.cert-date` | 日期 |

## 版面数值
| 项目 | 值 | 备注 |
|---|---|---|
{tbl}

## 文字内容（非 CSS，需在系统产生 HTML 时处理）
- 证明文字（`{{cn}}` 中文名、`{{en}}` 英文名、`{{ic}}` 身份证）：

    {tpl}

- 表头：`{hy}` / `{hs}` / `{hp}`
- 页数格式：`{ptpl}`；每页最多 {per} 行
- 日期格式：`21<sup>st</sup> November 2026`（日 + 上标序数 + 英文月份 + 年）
- 团体名称：{curnote}
""".format(ver=__version__, now=datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), tbl=tbl, tpl=tpl,
           pw=("%g" % _n(L.get("pageW"), 21)), ph=("%g" % _n(L.get("pageH"), 29.7)),
           hy=L.get("headY", ""), hs=L.get("headS", ""), hp=L.get("headP", ""), ptpl=L.get("pageTpl", ""),
           per=L.get("rowsPerPage", 10),
           curnote=("请依 `curricular.json` / `团体名称对照.csv` 统一中英文名称（%d 项；`years` 表示只在那些年份套用，"
                    "`aliases` 为系统里可能出现的其他写法）。" % len(ent)) if ent else "（未设定对照表）")


def curricular_csv(entries: List[dict]) -> str:
    buf = io.StringIO()
    wr = csv.writer(buf)
    wr.writerow(["中文名称 cn", "英文名称 en", "适用年份 years", "其他写法 aliases"])
    for e in entries:
        ys = e.get("years") or []
        yr = ("%d-%d" % (ys[0], ys[-1]) if len(ys) > 2 and ys[-1] - ys[0] == len(ys) - 1 else ",".join(map(str, ys)))
        wr.writerow([e.get("cn", ""), e.get("en", ""), yr, " | ".join(e.get("aliases") or [])])
    return "﻿" + buf.getvalue()   # BOM：Excel 直接开不乱码


def export(L: dict) -> Dict[str, object]:
    out = os.path.join(paths.P.output, OUT_DIRNAME)
    os.makedirs(out, exist_ok=True)
    cur = curricular.load()
    files = {
        "certificate-print.css": build_css(L),
        "sample.html": build_sample(L),
        "说明-spec.md": build_spec(L, cur),
        "layout.json": json.dumps({k: v for k, v in L.items() if k not in ("bgImage", "bgShow", "bgOpacity", "bg")},
                                  ensure_ascii=False, indent=2),
    }
    if cur.get("entries"):
        files["curricular.json"] = json.dumps({"societies": cur["entries"]}, ensure_ascii=False, indent=1)
        files["团体名称对照.csv"] = curricular_csv(cur["entries"])
    for name, text in files.items():
        with open(os.path.join(out, name), "w", encoding="utf-8", newline="") as f:
            f.write(text)
    logger.log("已导出 IT 规格包 %s（%d 个文件）" % (os.path.relpath(out, paths.P.base), len(files)))
    return {"dir": os.path.relpath(out, paths.P.base).replace("\\", "/"), "files": sorted(files)}
