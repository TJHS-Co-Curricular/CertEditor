# CLAUDE.md — Curricular-Certificate / CertEditor 项目说明（给 Claude 的长期记忆）

> 任何电脑上的 Claude（Claude Code / Cowork / claude.ai）处理本项目前先读这份文件。
> 做了会影响下面内容的决定后，**同步更新本文件**（以及 claude.ai Project 里的同名文档）。
> 沟通用**简体中文**，回答简洁。

## 1. 项目目的
学校系统导出的「联课证书」HTML（`Result/*.html`，GBK，
每位学生一页，绝对定位，单位 cm）→ 做成可编辑资料 → **准确套印在预印好的证书纸（有学校抬头的特殊纸）上**。

## 2. 使用者的硬性要求（不可违反）
- Python 写，打包成 **单一 `CertEditor_Portable.exe`（PyInstaller onefile）**，免安装、可携。
- **必须有黑色命令窗口**（`--console`），显示日志；关闭窗口 = 结束程序。
- **不要 desktop app 外壳**（不要 pywebview / Electron / Tk 窗口）→ 用本地 HTTP 服务 + 默认浏览器打开编辑器。
- 执行时只用 **Python 标准库**（打包工具 PyInstaller 除外）。
- 打印输出必须与原始 HTML **位置完全一致**（已验证误差 < 0.005 cm），适合特殊纸张套印。
- `Result/` 只读，永不修改原始 HTML。
- 设定集中在 `config/`（`CertEditor.ini`、`settings.json`、底图），与学生资料 `data/` 分开。
- 局域网访问与端口可在 `config/CertEditor.ini` 设定（LanAccess / Port / AutoPort / OpenBrowser / AllowIPs）。
- 手动改 `settings.json` 或替换底图要自动重新载入（约 2 秒轮询）。
- 版本号统一（`src/certeditor/__init__.py` 的 `__version__`），显示在启动画面、窗口标题、编辑器左上角、exe 档案内容；日志写入 `logs/`。

## 3. 项目结构
```
CertEditor.py               启动器（PyInstaller 入口；把 src 加入 sys.path）
build.bat                   .buildenv venv → pip -r requirements-build.txt → 跑测试 → PyInstaller → 复制 exe 到根目录
requirements-build.txt      pyinstaller>=6
pyproject.toml / README.md / CHANGELOG.md / .editorconfig / .gitignore
scripts/make_version_info.py   产生 Windows 版本资讯（--version-file）
src/certeditor/
  __init__.py   __version__、__title__、__app_name__="CertEditor"
  app.py        main()：路径→迁移→日志→ini→单一执行个体检查→起服务→开浏览器
  paths.py      执行时文件夹 + 旧版迁移（CertEditor_Data→data、Output→output、exe 旁 ini→config/CertEditor.ini）
  logger.py     out()/log()/error()：同时写命令窗口与 logs/certeditor-YYYY-MM-DD.log（保留 30 天）
  settings.py   ini 解析、settings.json、resolve_bg()（bgImage 路径 → 否则 config/background.*）、cfg_sig()
  parser.py     解析 Result HTML（charset 侦测，GBK→gb18030；多页学生合并）
  storage.py    data/<班级>.json 原子写入 + .bak；safe_name() 防路径穿越
  server.py     ThreadingHTTPServer + 路由表；API 见 §5
  web/editor.html  单文件编辑器（HTML/CSS/JS，无外部依赖）
tests/          unittest（python -m unittest discover -s tests）；helpers.py 生成**合成**GBK 测试 HTML（不含真实学生资料）
```
执行时（exe 旁）：`Result/`（来源）、`config/`、`data/`、`output/`（导出HTML）、`logs/`。

## 4. 版面 / 打印关键事实（改动前必读）
- 原始 HTML **没有 doctype → quirks 模式**。预览与打印都在 **无 doctype 的 iframe**（about:blank + document.write）里渲染，
  否则行高会偏。不要改成 standards 模式。
- 原始 `@page{margin:0.5cm}`、版心 20×28.7 cm → 编辑器用 `@page{size:A4;margin:0}` + 整体偏移 offX=offY=0.5 cm。
- 证明文字区块：left 6.6、top 6.6、width 12 cm、12pt；字体 `"Times New Roman", KaiTi…`。
- 表格：left 1、top 12.5 cm；原表 td 宽 2/9/9 cm 但被 18 cm 容器压缩 → **实际栏宽 1.93 / 8.05 / 8.02 cm**；
  `border-collapse:separate; border-spacing:0`、td padding 1px、表头底线 2px。
- 表头上下微调（settings.json `table.*`）：`headLineDy`（表头底线）、`headDyY` / `headDyS` / `headDyP`（年份/团体/职位文字），
  单位 cm、正数往下，只移动该项目不影响其他行；底线用 `td::after` 的 border 画（border 才会被打印），0 时与原版逐像素一致。
- 团体名称映射（v1.3）：`config/curricular.json` → `src/certeditor/curricular.py` 解析（多种格式，见模组说明），
  `GET /api/curricular`、`POST /api/curricular-template`；编辑器 `socFor(row)` 在**打印/预览/导出时**替换名称，
  学生资料不改；`settings.mapSocieties` 开关。项目可带 `years`（v1.3.1）：同名多个候选时
  先取年份符合的 → 再取不限年份的 → 否则打印原名（`pickByYear`）。前端状态用 `S.curric` / `S.curIdx`（**`S.cur` 是目前学生索引，勿重用**）。
- IT 规格包（v1.4）：`src/certeditor/itspec.py` 依编辑器送来的 `S.set` 产生 `output/IT-spec/`
  （CSS 选择器对应 Result 原结构 `.pagebreak > div:nth-of-type(1..4)`、`tr.line_btm`、`tr[valign=top]`，并附语意 class）。
  版面规则改动时 **CSS 也要同步改**，并重跑验证：真实 Result 加 `<link>` 后打印须与编辑器逐像素相同。
  注意 td 的 CSS width 不含左右 1px padding → 栏宽写 `calc(Xcm - 2px)`；整体偏移用 `.pagebreak{position:relative;left/top}` + `@page margin:0`。
- 页数 left 1.5 / 日期 left 10.5，bottom 1.0 cm（相对 28.7 cm 版心底部）。分页（v1.5）：`pageMode` 默认 `auto` → `autoBreaks()` 在隐藏 quirks iframe 量每行高度，表格底部 ≤ `tableBottom`（版心顶端起算，默认 26.5 cm）；
  `fixed` 才用 `rowsPerPage`（10）。超过自动分页「Page i of n」。
- 日期格式 `21<sup>st</sup> November 2026`；全班共用，可自订文字。
- 模板占位符：`{cn}` 中文名、`{en}` 英文名、`{ic}` 身份证。
- 底图（空白证书纸扫描）只在屏幕显示、不打印；上传时浏览器端缩到 ~200 dpi JPEG；可调 bg.left/top/width/height。

## 5. 已踩过的坑（不要回退）
- **使用者电脑会卡住本机的大型二进制 HTTP 回应**（防毒网页防护 / VPN / 过滤驱动；症状：底图只显示一半、Failed to fetch、
  测试 3 MB 下载 timeout）。→ 底图走 `GET /api/sheet-image-part?i=N`（JSON+base64，每段 32 KB，重试 3 次、核对大小），
  二进制 `/api/sheet-image` 只作后备；所有回应 32 KB 分块写出。页面/JSON ≤ 60 KB 正常。
- 同一台电脑上**约 64 KB 以上的本机回应一律会卡住**（与类型无关，页面 / JSON 也会）→ `_send()` 对 ≥1 KB 的文字回应 gzip
  （浏览器与测试都送 `Accept-Encoding: gzip`），加大 SO_SNDBUF；**任何回应压缩后都要 < 48 KB**（测试有检查页面与大班级资料）。
  editor.html 继续变大时要留意压缩后大小。验证方法：用每条连线只转送 64 KB 的代理跑浏览器。
- 同一台电脑也会**随机重置任何本机连线**（WinError 10054，与大小无关）→ 编辑器 `api()` 与测试 `req()` 一律重试
  （API 必须保持幂等才能安全重试）；底图分段每段重试 5 次；测试底图用 ~0.9 MB。
  新增的请求 / 测试都要走这两个会重试的函数，不要直接 fetch / urlopen（诊断用的 raw 测试除外）。
- API 用中性名称避免广告拦截误挡：`/api/sheet-image(-part)`、`/api/console`（旧 `/api/bg`、`/api/log` 保留相容）。
- 底图每次重新渲染不可重新下载 → 载入一次后用同一个 blob: URL。
- 启动时**先载入班级资料，底图背景载入**（底图卡住不可阻塞资料）。
- Windows 上 `SO_REUSEADDR` 会让两个程序绑同一端口 → `allow_reuse_address = os.name != "nt"`；
  同一文件夹已在执行时不再开第二个服务，改为打开已在执行的编辑器（`/api/ping` 比对 base 目录）。
- 设定自动重新载入要避开自己保存造成的变更（`S.saving`、`S.lastBgSig`）。

## 6. 开发 / 验证流程
- 改完必跑：`python -m unittest discover -s tests`（build.bat 也会跑，失败就不打包）。
- 动到渲染/版面：用 Playwright 把原始 `Result/*.html` 与编辑器导出页各渲染一次，比对每行 `tr` 的 top（cm），须一致。
- 原始码执行：`python CertEditor.py [--no-browser]`（base 目录 = 项目根；可用环境变量 `CERTEDITOR_HOME` 覆盖）。
- **个人资料屏蔽**：本文件、Project 文档、记忆、程序码、测试、提交记录里**不写任何个人资料**
  （使用者姓名/邮箱/所在地、学校名称与网址、学生姓名/身份证、本机路径）。举例只用合成资料（如「测试甲 / 000000000001」）。
- **绝不提交学生个人资料**：`Result/`、`data/`、`output/`、`logs/` 已在 `.gitignore`；测试只用合成资料。
- 版本变更：改 `__version__` + 写 `CHANGELOG.md`。

## 7. 环境备注
- Cowork 云端环境无法下载 Windows Python（python.org 被挡），**不能在云端产出 Windows exe** → 使用者自己双击 `build.bat`，
  或用 GitHub Actions（`.github/workflows/build.yml`，windows-latest 执行 `build.bat --no-pause`）。
- 透过 Cowork 写入使用者电脑时，`.github/` 属受保护路径无法写入，要请使用者手动放。
- 写回使用者文件夹后要核对文件大小（曾发生写入旧版本内容的情况）。

## 8. 待办 / 可能的下一步
- 已完成：v1.1.0 在使用者电脑打包成功；旧文件夹已迁移到 data/ output/ config/，旧 `editor.html`、`CertEditor_README.md` 已删除。
- `.github/workflows/build.yml` 需使用者手动放入（Cowork 无法写 `.github/`）。
- 可考虑：多人同时编辑的冲突提示（目前以最后保存为准）。
