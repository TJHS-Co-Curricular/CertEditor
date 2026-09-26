"""产生 PyInstaller --version-file 用的 Windows 版本资讯（exe 右键 → 内容 → 详细资料）。

用法: python scripts/make_version_info.py <输出文件>
"""
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))

from certeditor import __app_name__, __company__, __title__, __version__  # noqa: E402

TEMPLATE = """# UTF-8
VSVersionInfo(
  ffi=FixedFileInfo(filevers={t}, prodvers={t}, mask=0x3f, flags=0x0, OS=0x40004,
                    fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('040904B0', [
      StringStruct('CompanyName', {company!r}),
      StringStruct('FileDescription', {title!r}),
      StringStruct('FileVersion', {v!r}),
      StringStruct('InternalName', {app!r}),
      StringStruct('OriginalFilename', 'CertEditor_Portable.exe'),
      StringStruct('ProductName', {app!r}),
      StringStruct('ProductVersion', {v!r})])]),
    VarFileInfo([VarStruct('Translation', [1033, 1200])])
  ]
)
"""


def main(out: str) -> None:
    nums = [int(x) for x in __version__.split(".")[:3]]
    nums += [0] * (4 - len(nums))
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(TEMPLATE.format(t=tuple(nums), company=__company__, title=__title__, v=__version__, app=__app_name__))
    print(__version__)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, ".buildwork", "version_info.txt"))
