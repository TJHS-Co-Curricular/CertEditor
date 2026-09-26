"""本地 HTTP 服务：提供 editor.html 与 JSON API。"""
import base64
import hashlib
import ipaddress
import json
import os
import socket
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Optional, Tuple

from . import __app_name__, __version__, logger, paths, settings, storage
from .settings import IniConfig

CLIENT_DISCONNECTED = (BrokenPipeError, ConnectionAbortedError, ConnectionResetError)
WRITE_BLOCK = 32 * 1024          # 分块写出，减少部分防毒 / 网络过滤驱动卡住大回应的机会
IMAGE_CHUNK = 32 * 1024          # 底图以 JSON(base64) 分段传送，每段原始大小


class ServerState:
    ini = IniConfig()
    seen_ips: set = set()


STATE = ServerState()


def lan_ips():
    ips = set()
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("10.255.255.255", 1))
            ips.add(s.getsockname()[0])
    except OSError:
        pass
    try:
        ips.update(socket.gethostbyname_ex(socket.gethostname())[2])
    except OSError:
        pass
    return sorted(i for i in ips if not i.startswith(("127.", "169.254.")))


def client_allowed(ip: str, ini: IniConfig) -> bool:
    try:
        a = ipaddress.ip_address(ip.split("%")[0])
    except ValueError:
        return False
    if getattr(a, "ipv4_mapped", None):
        a = a.ipv4_mapped
    if a.is_loopback:
        return True
    if not ini.lan:
        return False
    return not ini.allow or any(a in n for n in ini.allow)


class Handler(BaseHTTPRequestHandler):
    server_version = "%s/%s" % (__app_name__, __version__)

    def log_message(self, fmt, *args):  # 静音预设 access log
        pass

    # ------------------------------------------------------------ helpers
    def _send(self, code: int, body, ctype: str = "application/json; charset=utf-8", headers=None) -> None:
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False)
        if isinstance(body, str):
            body = body.encode("utf-8")
        try:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            for k, v in (headers or {}).items():
                self.send_header(k, v)
            if "Cache-Control" not in (headers or {}):
                self.send_header("Cache-Control", "no-store")
            self.end_headers()
            if self.command != "HEAD":
                for i in range(0, len(body), WRITE_BLOCK):
                    self.wfile.write(body[i:i + WRITE_BLOCK])
        except CLIENT_DISCONNECTED:
            logger.log("连线中断（%s %s）" % (self.command, self.path.split("?")[0]))

    def _body(self) -> bytes:
        n = int(self.headers.get("Content-Length") or 0)
        buf = bytearray()
        while len(buf) < n:
            chunk = self.rfile.read(min(1 << 20, n - len(buf)))
            if not chunk:
                break
            buf += chunk
        if len(buf) != n:
            raise ValueError("上传不完整 (%d/%d bytes)" % (len(buf), n))
        return bytes(buf)

    def _q(self) -> Tuple[str, dict]:
        u = urllib.parse.urlparse(self.path)
        return u.path, {k: v[0] for k, v in urllib.parse.parse_qs(u.query).items()}

    def _guard(self) -> bool:
        ip = self.client_address[0]
        ok = client_allowed(ip, STATE.ini)
        if ip not in STATE.seen_ips:
            STATE.seen_ips.add(ip)
            if not ok:
                logger.log("拒绝访问: " + ip)
            elif not ipaddress.ip_address(ip.split("%")[0]).is_loopback:
                logger.log("局域网连线: " + ip)
        if not ok:
            self._send(403, {"error": "forbidden"})
        return ok

    def _dispatch(self, table) -> None:
        if not self._guard():
            return
        path, q = self._q()
        fn = table.get(path)
        if not fn:
            return self._send(404, {"error": "not found"})
        try:
            fn(self, q)
        except CLIENT_DISCONNECTED:
            logger.log("连线中断（%s %s）" % (self.command, path))
        except ValueError as e:
            logger.log("请求被拒绝 %s: %s" % (path, e))
            self._send(400, {"error": str(e)})
        except Exception as e:
            logger.error("处理 %s %s 失败" % (self.command, path))
            self._send(500, {"error": str(e)})

    def do_GET(self):
        self._dispatch(GET_ROUTES)

    def do_HEAD(self):
        self._dispatch(GET_ROUTES)

    def do_POST(self):
        self._dispatch(POST_ROUTES)

    # ------------------------------------------------------------ GET
    def get_index(self, q):
        with open(os.path.join(paths.web_dir(), "editor.html"), "rb") as f:
            self._send(200, f.read(), "text/html; charset=utf-8")

    def get_state(self, q):
        P = paths.P
        self._send(200, {"app": __app_name__, "version": __version__, "pid": os.getpid(),
                         "classes": storage.list_classes(), "settings": settings.load_settings(),
                         "cfg": settings.cfg_sig(), "baseDir": P.base,
                         "dirs": {k: os.path.relpath(getattr(P, k), P.base)
                                  for k in ("result", "config", "data", "output", "logs")}})

    def get_ping(self, q):
        self._send(200, {"app": __app_name__, "version": __version__, "pid": os.getpid(), "base": paths.P.base})

    def get_cfgsig(self, q):
        self._send(200, settings.cfg_sig())

    def get_class(self, q):
        self._send(200, storage.load_class(q.get("name", ""), q.get("reimport") == "1"))

    def get_bg(self, q):
        p = settings.resolve_bg()
        if not p:
            return self._send(404, {"error": "no background"})
        with open(p, "rb") as f:
            data = f.read()
        etag = '"%s"' % hashlib.md5(data).hexdigest()
        if self.headers.get("If-None-Match") == etag:
            return self._send(304, b"", "application/octet-stream", {"ETag": etag, "Cache-Control": "no-cache"})
        ext = p.rsplit(".", 1)[-1].lower()
        self._send(200, data, settings.IMG_TYPES.get(ext, "application/octet-stream"),
                   {"ETag": etag, "Cache-Control": "no-cache"})
        logger.log("提供底图 %s (%d KB) -> %s" % (os.path.relpath(p, paths.P.base), len(data) // 1024,
                                              self.client_address[0]))

    def get_bg_chunk(self, q):
        """底图分段（JSON + base64）。有些电脑的防毒网页防护 / 网络过滤驱动会卡住本机的大型
        二进制回应（症状：底图只显示一半、Failed to fetch），JSON 小段传送则不受影响。"""
        p = settings.resolve_bg()
        if not p:
            return self._send(404, {"error": "no background"})
        with open(p, "rb") as f:
            data = f.read()
        n = max(1, -(-len(data) // IMAGE_CHUNK))
        i = int(q.get("i", "0"))
        if not 0 <= i < n:
            raise ValueError("chunk 超出范围")
        part = data[i * IMAGE_CHUNK:(i + 1) * IMAGE_CHUNK]
        ext = p.rsplit(".", 1)[-1].lower()
        self._send(200, {"i": i, "chunks": n, "total": len(data), "md5": hashlib.md5(data).hexdigest(),
                         "type": settings.IMG_TYPES.get(ext, "application/octet-stream"),
                         "data": base64.b64encode(part).decode("ascii")})
        if i == n - 1:
            logger.log("提供底图 %s (%d KB, %d 段) -> %s" % (os.path.relpath(p, paths.P.base), len(data) // 1024, n,
                                                       self.client_address[0]))

    # ------------------------------------------------------------ POST
    def post_class(self, q):
        data = json.loads(self._body().decode("utf-8"))
        saved = storage.save_class(q.get("name", ""), data)
        self._send(200, {"ok": True, "savedAt": saved})

    def post_settings(self, q):
        settings.save_settings(json.loads(self._body().decode("utf-8")))
        self._send(200, {"ok": True, "cfg": settings.cfg_sig()})

    def post_export(self, q):
        name = storage.safe_name(q.get("name", ""))
        out = os.path.join(paths.P.output, name + "_print.html")
        with open(out, "wb") as f:
            f.write(self._body())
        logger.log("已导出 " + out)
        self._send(200, {"ok": True, "path": out})

    def post_bg(self, q):
        body = self._body()
        settings.save_background(body, q.get("ext") or "jpg")
        self._send(200, {"ok": True, "size": len(body), "cfg": settings.cfg_sig()})

    def post_delete(self, q):
        storage.delete_class_data(q.get("name", ""))
        self._send(200, {"ok": True})

    def post_log(self, q):
        logger.log("[浏览器] " + self._body().decode("utf-8", "replace")[:500])
        self._send(200, {"ok": True})


GET_ROUTES = {"/": Handler.get_index, "/index.html": Handler.get_index, "/api/state": Handler.get_state,
              "/api/ping": Handler.get_ping, "/api/cfgsig": Handler.get_cfgsig, "/api/class": Handler.get_class,
              "/api/sheet-image": Handler.get_bg, "/api/bg": Handler.get_bg,
              "/api/sheet-image-part": Handler.get_bg_chunk}
POST_ROUTES = {"/api/class": Handler.post_class, "/api/settings": Handler.post_settings,
               "/api/export": Handler.post_export, "/api/sheet-image": Handler.post_bg, "/api/bg": Handler.post_bg,
               "/api/delete": Handler.post_delete, "/api/console": Handler.post_log, "/api/log": Handler.post_log}
# 注：/api/sheet-image、/api/console 用中性名称，避免被广告拦截扩充功能误挡（/api/bg、/api/log 保留相容）


class Server(ThreadingHTTPServer):
    daemon_threads = True
    # Windows 的 SO_REUSEADDR 会让两个程序同时绑同一个端口 → 请求乱跳，所以 Windows 下关闭
    allow_reuse_address = os.name != "nt"

    def handle_error(self, request, client_address):
        logger.error("连线处理错误 %s" % (client_address,))


def probe_instance(port: int, timeout: float = 0.6) -> Optional[dict]:
    """检查该端口是否已有 CertEditor 在执行。"""
    try:
        with urllib.request.urlopen("http://127.0.0.1:%d/api/ping" % port, timeout=timeout) as r:
            d = json.loads(r.read().decode("utf-8"))
            return d if d.get("app") == __app_name__ else None
    except Exception:
        return None


def make_server(host: str, port: int, auto: bool) -> Tuple[Server, int]:
    last = None
    for p in (range(port, min(port + 50, 65536)) if auto else [port]):
        try:
            return Server((host, p), Handler), p
        except OSError as e:
            last = e
    raise OSError("端口 %d 无法使用（可能被占用）：%s" % (port, last))
