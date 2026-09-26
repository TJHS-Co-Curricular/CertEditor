"""设定：config/CertEditor.ini（启动 / 网络）与 config/settings.json（版面 / 底图）。"""
import configparser
import ipaddress
import json
import os
import re
from dataclasses import dataclass, field
from typing import List, Optional, Union

from . import logger, paths
from .storage import write_json

IMG_EXT = ("png", "jpg", "jpeg", "gif", "webp", "bmp")
IMG_TYPES = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
             "gif": "image/gif", "webp": "image/webp", "bmp": "image/bmp"}

DEFAULT_INI = """; ============================================================
;  联课证书编辑器 CertEditor 启动设定（修改后重新开启程序生效）
; ============================================================
[Server]
; 允许局域网 (LAN) 其他电脑/手机访问：true / false
;   false = 只有本机能打开 (127.0.0.1)
;   true  = 同一网络的其他设备可用 http://本机IP:端口/ 打开
;           第一次开启时 Windows 防火墙可能会询问，请按「允许」
LanAccess = false

; 端口 (1024-65535)
Port = 8765

; 端口被占用时自动改用下一个可用端口：true / false
;   false = 端口被占用就报错（LAN 模式建议 false，网址才固定）
AutoPort = true

; 开启程序时自动打开浏览器：true / false
OpenBrowser = true

; 只允许这些 IP 访问（LAN 模式才有作用），用逗号分隔，可写网段
;   例：AllowIPs = 192.168.1.0/24, 192.168.0.50
;   留空 = 同一网络的所有设备都可以访问（本机永远可以）
AllowIPs =
"""


@dataclass
class IniConfig:
    lan: bool = False
    port: int = 8765
    autoport: bool = True
    browser: bool = True
    allow: List[Union[ipaddress.IPv4Network, ipaddress.IPv6Network]] = field(default_factory=list)


def _bool(v, d=False) -> bool:
    if v is None:
        return d
    return str(v).strip().lower() in ("1", "true", "yes", "on", "y", "是", "开")


def load_ini(path: Optional[str] = None) -> IniConfig:
    path = path or paths.P.ini
    if not os.path.exists(path):
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8-sig") as f:
                f.write(DEFAULT_INI)
            logger.out("  已建立预设设定档 " + path)
        except OSError as e:
            logger.out("  [警告] 无法建立 %s: %s" % (path, e))
    cp = configparser.ConfigParser(inline_comment_prefixes=(";", "#"))
    try:
        cp.read(path, encoding="utf-8-sig")
    except Exception as e:
        logger.out("  [警告] %s 读取失败，使用预设值: %s" % (path, e))
    sec = cp["Server"] if cp.has_section("Server") else {}
    cfg = IniConfig(lan=_bool(sec.get("LanAccess"), False),
                    autoport=_bool(sec.get("AutoPort"), True),
                    browser=_bool(sec.get("OpenBrowser"), True))
    try:
        cfg.port = int(str(sec.get("Port", "8765")).strip() or 8765)
        if not 1 <= cfg.port <= 65535:
            raise ValueError
    except ValueError:
        logger.out("  [警告] Port 设定无效，改用 8765")
        cfg.port = 8765
    for item in re.split(r"[,\s]+", str(sec.get("AllowIPs", "") or "")):
        if item:
            try:
                cfg.allow.append(ipaddress.ip_network(item, strict=False))
            except ValueError:
                logger.out("  [警告] AllowIPs 无效项目已忽略: " + item)
    return cfg


# ------------------------------------------------------------------ settings.json
def load_settings() -> Optional[dict]:
    p = paths.P.settings
    if os.path.exists(p):
        try:
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            logger.error("settings.json 读取失败，使用默认值", exc=False)
    return None


def save_settings(data: dict) -> None:
    write_json(paths.P.settings, data)
    logger.log("已保存版面设置")


def _is_img(name: str) -> bool:
    return name.rsplit(".", 1)[-1].lower() in IMG_EXT


def config_backgrounds() -> List[str]:
    c = paths.P.config
    return [os.path.join(c, f) for f in sorted(os.listdir(c))
            if f.lower().startswith("background.") and _is_img(f)]


def resolve_bg(st: Optional[dict] = None) -> Optional[str]:
    """底图：settings.json 的 bgImage（相对程序目录 / config，或绝对路径）；否则 config/background.*"""
    st = load_settings() if st is None else st
    p = ((st or {}).get("bgImage") or "").strip().strip('"')
    if p:
        cands = [p] if os.path.isabs(p) else [os.path.join(paths.P.base, p), os.path.join(paths.P.config, p)]
        for c in cands:
            if os.path.isfile(c):
                return os.path.normpath(c)
    bgs = config_backgrounds()
    return bgs[0] if bgs else None


def file_sig(path: Optional[str]) -> str:
    if not path:
        return ""
    try:
        s = os.stat(path)
        return "%s|%d|%d" % (path, s.st_mtime_ns, s.st_size)
    except OSError:
        return ""


def cfg_sig() -> dict:
    st = load_settings() or {}
    bg = resolve_bg(st)
    want = (st.get("bgImage") or "").strip()
    rel = os.path.relpath(bg, paths.P.base).replace("\\", "/") if bg else ""
    missing = bool(want) and (not bg or os.path.basename(bg) != os.path.basename(want.replace("\\", "/")))
    return {"settings": file_sig(paths.P.settings), "bg": file_sig(bg), "bgPath": rel,
            "bgMissing": want if missing else ""}


def save_background(body: bytes, ext: str) -> None:
    ext = (ext or "jpg").lower().strip(".")
    if ext not in IMG_EXT:
        raise ValueError("不支持的图片格式")
    for p in config_backgrounds():
        os.remove(p)
    if body:
        with open(os.path.join(paths.P.config, "background." + ext), "wb") as f:
            f.write(body)
        logger.log("已设置底图 config/background.%s (%d KB)" % (ext, len(body) // 1024))
    else:
        logger.log("已移除底图")
