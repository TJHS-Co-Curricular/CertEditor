import os
import shutil
import sys
import tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))

from certeditor import logger, paths  # noqa: E402

PAGE = """<div class="pagebreak relative">
	<div class="absolute" style="width:12cm;top: 6.6cm;left: 6.6cm;font-size:12pt;">
	学生 {cn} (身份证号码: {ic})<br>在籍本校期间，曾积极参与各项联课活动或担任执委之职，<br>任劳任怨，极尽职责，特此予以证明，以资奖励。<br><br>This is to certify that {en}<br>( N.R.I.C. No. {ic}) had actively participated<br>in the following co-curricular activities of this school and had<br>proved himself/herself to be responsible and capable of carrying<br>out his/her duties.	</div>
	<div class="absolute" style="top: 12.5cm;left: 1cm;table-layout: fixed;width: 18cm;">
		<table border="0" cellspacing="0">
			<tbody><tr class="line_btm">
				<td style="width: 2cm;">年 YEAR</td>
				<td style="width: 9cm;">联课团体名称 NAME OF SOCIETIES</td>
				<td style="width: 9cm;">职位 POSITION</td>
			</tr>
			{rows}		</tbody></table>
	</div>
	<!-- 页数 -->
	<div class="center absolute" style="left: 1.5cm;bottom: 1.0cm;">
		Page {i} of {n}	</div>
	<!-- 日期 -->
	<div class="center absolute" style="left: 10.5cm;bottom: 1.0cm;">
		21<sup>st</sup> November 2026	</div>
</div>"""
ROW = """<tr valign="top" style="font-size:12pt;">
								<td>{y}</td>
								<td>{sc}<br>{se}</td>
								<td>{pc}<br>{pe}</td>
							</tr>"""


def make_result_html(students):
    """students: [(cn, ic, en, [(year, socCn, socEn, posCn, posEn), ...]), ...]；超过 10 行自动分页。"""
    body = ""
    for cn, ic, en, rows in students:
        chunks = [rows[i:i + 10] for i in range(0, len(rows), 10)] or [[]]
        for i, ch in enumerate(chunks, 1):
            r = "".join(ROW.format(y=a, sc=b, se=c, pc=d, pe=e) for a, b, c, d, e in ch)
            body += PAGE.format(cn=cn, ic=ic, en=en, rows=r, i=i, n=len(chunks))
    doc = ('<html><head><meta http-equiv="Content-Type" content="text/html; charset=GBK">'
           "<title>t</title></head><body>" + body + "</body></html>")
    return doc.encode("gbk")


class TempHome:
    """建立临时程序目录并设定 paths.P。"""

    def __enter__(self):
        self.dir = tempfile.mkdtemp(prefix="certeditor-test-")
        self.P = paths.configure(self.dir)
        return self

    def setup(self):
        self.P.ensure()
        return self.P

    def __exit__(self, *a):
        logger.close()
        shutil.rmtree(self.dir, ignore_errors=True)
