"""同时输出到黑色命令窗口与 logs/certeditor-YYYY-MM-DD.log。"""
import datetime
import os
import sys
import threading
import time
import traceback
from typing import Optional

_lock = threading.Lock()
_file = None
_path: Optional[str] = None
KEEP_DAYS = 30

try:
    sys.stdout.reconfigure(errors="replace")
    sys.stderr.reconfigure(errors="replace")
except Exception:
    pass


def setup(logs_dir: str) -> Optional[str]:
    global _file, _path
    try:
        os.makedirs(logs_dir, exist_ok=True)
        _path = os.path.join(logs_dir, "certeditor-%s.log" % datetime.date.today().isoformat())
        _file = open(_path, "a", encoding="utf-8", buffering=1)
        _prune(logs_dir)
    except OSError as e:
        _file = None
        print("  [警告] 无法写入日志文件: %s" % e)
    return _path


def _prune(logs_dir: str) -> None:
    cutoff = time.time() - KEEP_DAYS * 86400
    for name in os.listdir(logs_dir):
        p = os.path.join(logs_dir, name)
        if name.startswith("certeditor-") and name.endswith(".log") and os.path.getmtime(p) < cutoff:
            try:
                os.remove(p)
            except OSError:
                pass


def _write(line: str) -> None:
    with _lock:
        try:
            print(line, flush=True)
        except Exception:
            pass
        if _file:
            try:
                _file.write(line + "\n")
            except Exception:
                pass


def out(msg: str = "") -> None:
    """不带时间的输出（启动画面）。"""
    _write(msg)


def log(msg: str) -> None:
    _write(time.strftime("[%H:%M:%S] ") + str(msg))


def error(msg: str, exc: bool = True) -> None:
    _write(time.strftime("[%H:%M:%S] [错误] ") + str(msg))
    if exc:
        tb = traceback.format_exc()
        if tb and tb.strip() != "NoneType: None":
            _write(tb.rstrip())


def close() -> None:
    global _file
    if _file:
        _file.close()
        _file = None
