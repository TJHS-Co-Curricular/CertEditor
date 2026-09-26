# Changelog

## 1.1.0 — 2026-09-26
### 项目标准化
- 程序拆成 `src/certeditor/` 套件（app / paths / logger / settings / parser / storage / server），`CertEditor.py` 只作启动器。
- 编辑器页面移到 `src/certeditor/web/editor.html`。
- 新增单元测试 `tests/`，`build.bat` 打包前自动执行；使用独立的 `.buildenv` 虚拟环境。
- 新增 `pyproject.toml`、`requirements-build.txt`、`.editorconfig`、`CHANGELOG.md`。

### 执行时文件夹统一
- `CertEditor_Data/` → `data/`，`Output/` → `output/`，`CertEditor_Portable.ini` → `config/CertEditor.ini`（启动时自动迁移）。
- 新增 `logs/`：命令窗口内容同时写入 `certeditor-YYYY-MM-DD.log`，保留 30 天。

### 版本号
- 版本号统一来自 `certeditor.__version__`：启动画面、窗口标题、编辑器左上角、exe 档案内容。

### 修正
- 底图「Failed to fetch」/ 只显示一半：部分电脑（防毒网页防护、VPN、网络过滤驱动）会卡住本机的大型二进制回应。
  底图改为 JSON(base64) 每段 32 KB 分段下载并核对大小，每段失败重试 3 次；旧的二进制网址只作后备。
  所有回应改为 32 KB 分块写出；API 改用中性网址（`/api/sheet-image`、`/api/console`）。
- 测试：新增分段下载完整性测试；二进制传输在本机被卡住时，诊断测试会略过并说明原因，不再中断打包。
- 同一文件夹重复开启时，不再启动第二个服务，改为打开已在执行的编辑器（避免两个程序同时写资料）。
- 启动时先载入班级资料，底图在背景载入；预览框同步建立。

## 1.0.0 — 2026-09-26
- 第一版：导入 Result HTML、学生资料编辑、版面校准、底图、打印 / 导出、局域网访问设定。
