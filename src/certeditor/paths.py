"""程序目录与执行时文件夹。

执行时（exe 旁边）的标准结构::

    CertEditor_Portable.exe
    Result/        来源 HTML（学校系统导出，只读）
    config/        CertEditor.ini、settings.json、background.*
    data/          每个班级的编辑资料 <班级>.json（含 .bak）
    output/        「导出HTML」产生的可打印文件
    logs/          运行日志 certeditor-YYYY-MM-DD.log
"""
import os
import shutil
import sys
from dataclasses import dataclass
from typing import List, Optional

FROZEN = bool(getattr(sys, "frozen", False))

RESULT_DIRNAME = "Result"
CONFIG_DIRNAME = "config"
DATA_DIRNAME = "data"
OUTPUT_DIRNAME = "output"
LOGS_DIRNAME = "logs"
INI_NAME = "CertEditor.ini"
SETTINGS_NAME = "settings.json"


def app_base_dir() -> str:
    """exe 所在目录；原始码执行时为项目根目录；可用环境变量 CERTEDITOR_HOME 覆盖。"""
    env = os.environ.get("CERTEDITOR_HOME")
    if env:
        return os.path.abspath(env)
    if FROZEN:
        return os.path.dirname(os.path.abspath(sys.executable))
    # src/certeditor/paths.py -> 项目根目录
    return os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))


def web_dir() -> str:
    """内建网页资源（editor.html）所在目录。"""
    if FROZEN:
        return os.path.join(getattr(sys, "_MEIPASS", app_base_dir()), "certeditor", "web")
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")


@dataclass
class Paths:
    base: str
    result: str
    config: str
    data: str
    output: str
    logs: str
    ini: str
    settings: str

    def ensure(self) -> None:
        for d in (self.result, self.config, self.data, self.output, self.logs):
            os.makedirs(d, exist_ok=True)


def build(base: str) -> Paths:
    j = os.path.join
    cfg = j(base, CONFIG_DIRNAME)
    return Paths(base=base, result=j(base, RESULT_DIRNAME), config=cfg, data=j(base, DATA_DIRNAME),
                 output=j(base, OUTPUT_DIRNAME), logs=j(base, LOGS_DIRNAME),
                 ini=j(cfg, INI_NAME), settings=j(cfg, SETTINGS_NAME))


P: Optional[Paths] = None


def configure(base: Optional[str] = None) -> Paths:
    global P
    P = build(os.path.abspath(base or app_base_dir()))
    return P


# ------------------------------------------------------------------ migration
def _names(parent: str) -> List[str]:
    try:
        return os.listdir(parent)
    except OSError:
        return []


def _merge_move(src: str, dst: str, msgs: List[str], label: str) -> None:
    os.makedirs(dst, exist_ok=True)
    for name in _names(src):
        s, d = os.path.join(src, name), os.path.join(dst, name)
        if os.path.exists(d):
            msgs.append("  [略过] %s 已存在：%s" % (label, name))
            continue
        shutil.move(s, d)
    if not _names(src):
        os.rmdir(src)


def _migrate_dir(base: str, old: str, new: str, msgs: List[str]) -> None:
    names = _names(base)
    if old not in names:
        return
    src, dst = os.path.join(base, old), os.path.join(base, new)
    if old.lower() == new.lower() and new not in names:
        # 只改大小写（Windows 不分大小写，要经过暂存名）
        tmp = dst + ".migrating"
        os.rename(src, tmp)
        os.rename(tmp, dst)
    elif not os.path.exists(dst):
        os.rename(src, dst)
    else:
        _merge_move(src, dst, msgs, new)
    msgs.append("  已搬移 %s%s -> %s%s" % (old, os.sep, new, os.sep))


def _move_file(base: str, src: str, dst: str, msgs: List[str]) -> None:
    if os.path.isfile(src) and not os.path.exists(dst):
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.move(src, dst)
        msgs.append("  已搬移 %s -> %s" % (os.path.relpath(src, base), os.path.relpath(dst, base)))


def migrate(p: Paths) -> List[str]:
    """把旧版文件夹/文件搬到标准位置，回传讯息列表。"""
    msgs: List[str] = []
    _migrate_dir(p.base, "CertEditor_Data", DATA_DIRNAME, msgs)
    _migrate_dir(p.base, "Output", OUTPUT_DIRNAME, msgs)
    # 旧版把 settings.json / 底图放在资料夹里
    for folder in (p.data,):
        for name in _names(folder):
            low = name.lower()
            if low.startswith("settings.json") or low.startswith("background."):
                if low.startswith("background.") and any(n.lower().startswith("background.") for n in _names(p.config)):
                    continue
                _move_file(p.base, os.path.join(folder, name), os.path.join(p.config, name), msgs)
    # 旧版 ini 放在 exe 旁边
    for name in _names(p.base):
        if name.lower().endswith(".ini") and name.lower().startswith("certeditor"):
            _move_file(p.base, os.path.join(p.base, name), p.ini, msgs)
    return msgs
