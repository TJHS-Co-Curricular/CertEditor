"""程序入口：设定路径 → 搬移旧文件 → 日志 → 读 ini → 启动服务 → 打开浏览器。"""
import os
import sys
import threading
import webbrowser

from . import __title__, __version__, logger, paths, server, settings


def _pause(msg: str = "\n  按 Enter 结束...") -> None:
    try:
        input(msg)
    except (EOFError, KeyboardInterrupt):
        pass


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if os.name == "nt":
        os.system("title CertEditor %s - Curricular Certificate Editor" % __version__)

    P = paths.configure()
    moved = paths.migrate(P)
    P.ensure()
    log_file = logger.setup(P.logs)

    logger.out("=" * 64)
    logger.out("  %s  v%s" % (__title__, __version__))
    logger.out("=" * 64)
    for m in moved:
        logger.out(m)
    ini = settings.load_ini()
    server.STATE.ini = ini

    # 同一个文件夹已经有 CertEditor 在执行 → 直接打开它，避免两个程序同时写资料
    other = server.probe_instance(ini.port)
    if other and os.path.normcase(other.get("base", "")) == os.path.normcase(P.base):
        url = "http://127.0.0.1:%d/" % ini.port
        logger.out("  这个文件夹的 CertEditor 已经在执行中（PID %s，v%s）" % (other.get("pid"), other.get("version")))
        logger.out("  已帮你打开：" + url)
        logger.out("  如要重新启动，请先关闭另一个黑色窗口。")
        if "--no-browser" not in argv:
            webbrowser.open(url)
        _pause()
        return 1

    host = "0.0.0.0" if ini.lan else "127.0.0.1"
    try:
        httpd, port = server.make_server(host, ini.port, ini.autoport)
    except OSError as e:
        logger.error(str(e), exc=False)
        logger.out("  请修改 %s 的 Port，或把 AutoPort 设为 true。" % P.ini)
        _pause()
        return 2

    url = "http://127.0.0.1:%d/" % port
    rel = lambda p: os.path.relpath(p, P.base) + os.sep
    logger.out("  程序目录 : " + P.base)
    logger.out("  来源HTML : " + rel(P.result))
    logger.out("  编辑资料 : " + rel(P.data))
    logger.out("  设定     : " + rel(P.config) + "  (CertEditor.ini / settings.json / 底图)")
    logger.out("  导出     : " + rel(P.output))
    logger.out("  日志     : " + (os.path.relpath(log_file, P.base) if log_file else "(无法写入)"))
    logger.out("-" * 64)
    logger.out("  本机网址 : " + url)
    if ini.port != port:
        logger.out("  (端口 %d 被占用，已改用 %d)" % (ini.port, port))
    if ini.lan:
        ips = server.lan_ips()
        logger.out("  局域网   : 已开启")
        for ip in ips:
            logger.out("             http://%s:%d/" % (ip, port))
        if not ips:
            logger.out("             (找不到本机IP，请用 ipconfig 查看)")
        logger.out("  允许IP   : " + (", ".join(str(n) for n in ini.allow) if ini.allow else "同网络全部设备"))
        logger.out("  注意：多人同时编辑同一个班级时，以最后保存的为准。")
    else:
        logger.out("  局域网   : 关闭（在 config\\CertEditor.ini 设 LanAccess = true 开启）")
    logger.out("-" * 64)
    logger.out("  浏览器没有自动打开的话，请手动打开上面的网址。")
    logger.out("  关闭此黑色窗口 或 按 Ctrl+C 即可结束程序。")
    logger.out("=" * 64)
    logger.log("启动 v%s PID %d" % (__version__, os.getpid()))

    if ini.browser and "--no-browser" not in argv:
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        httpd.server_close()
        logger.log("程序已结束")
        logger.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
