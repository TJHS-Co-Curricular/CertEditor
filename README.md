# Curricular-Certificate · 联课证书编辑器 (CertEditor)

把学校系统导出的联课证书 HTML（`Result/*.html`）变成可编辑的资料，并准确套印到预印好的证书纸上。
单一 `CertEditor_Portable.exe`，免安装；带黑色命令窗口（显示日志），编辑器在浏览器中打开。

## 项目结构

```
Curricular-Certificate/
├─ CertEditor.py              启动器（PyInstaller 入口，也可 python CertEditor.py）
├─ build.bat                  一键打包 → CertEditor_Portable.exe
├─ requirements-build.txt     打包工具（PyInstaller）
├─ pyproject.toml             项目资讯 / 版本
├─ src/certeditor/
│  ├─ __init__.py             版本号 __version__
│  ├─ app.py                  程序入口（启动画面、单一执行个体、开浏览器）
│  ├─ paths.py                执行时文件夹 + 旧版自动迁移
│  ├─ logger.py               命令窗口 + logs/ 日志
│  ├─ settings.py             CertEditor.ini、settings.json、底图
│  ├─ parser.py               解析 Result/*.html（GBK）
│  ├─ storage.py              班级资料读写（原子写入 + .bak）
│  ├─ server.py               本地 HTTP 服务 / API
│  └─ web/editor.html         编辑器页面
├─ scripts/make_version_info.py   产生 exe 版本资讯
└─ tests/                     单元测试（python -m unittest discover -s tests）
```

## 执行时文件夹（exe 旁边）

| 文件夹 | 内容 |
|---|---|
| `Result/` | 来源 HTML（学校系统导出；程序只读，不会修改） |
| `config/` | `CertEditor.ini`（启动/网络）、`settings.json`（版面）、`background.*`（底图） |
| `data/` | 每个班级的编辑资料 `<班级>.json`（自动保存，保留 `.bak`） |
| `output/` | 「导出HTML」产生的可打印文件 |
| `logs/` | 运行日志 `certeditor-YYYY-MM-DD.log`（保留 30 天） |

旧版的 `CertEditor_Data/`、`Output/`、exe 旁的 `CertEditor_Portable.ini` 会在启动时自动搬到上面的位置。
`data/`、`output/`、`logs/`、`Result/` 含学生个人资料或可重新产生，已列入 `.gitignore`。

## 打包

1. 安装 Python 3.9+（python.org，勾选 *Add to PATH*）。
2. 双击 `build.bat`：建立 `.buildenv` → 安装 PyInstaller → **跑单元测试** → 打包 → 把 `CertEditor_Portable.exe` 复制到项目根目录。

开发时也可以直接执行：`python CertEditor.py`（或 `python CertEditor.py --no-browser`）。

## 使用

- `CertEditor_Portable.exe` 放在 `Result/` 旁边，双击。
- 同一个文件夹只会执行一个 CertEditor；重复开启会直接打开已在执行的那一个。
- 版本号显示在：黑色窗口标题 / 启动画面、编辑器左上角、exe「内容 → 详细资料」。

### `config/CertEditor.ini`

```ini
[Server]
LanAccess = false     ; true = 同网络的电脑/手机可用 http://本机IP:端口/ 访问
Port = 8765
AutoPort = true       ; 端口被占用时自动换下一个（LAN 建议 false，网址才固定）
OpenBrowser = true
AllowIPs =            ; 可选：只允许这些 IP / 网段，如 192.168.1.0/24
```
修改后重新开启程序生效。开启 LAN 时第一次 Windows 防火墙会询问，请选「允许」。
多人同时编辑同一个班级时，以最后保存的为准。

### 特殊纸张打印

- 打印对话框：边距 **无**、缩放 **100%**、不勾选「页眉和页脚」。
- 先用普通纸打「校准页」（cm 网格 + 区块外框），叠在证书纸上对光检查。
- 整体偏移：「版面 & 纸张校准」方向键（每次 0.1 cm）；个别区块：在预览中拖动或输入数值。
- 底图（只显示、不打印）：上传扫描图，或在 `settings.json` 写 `"bgImage": "Curricular-Certificate-Example.jpg"`（相对程序目录）。
  手动改 `settings.json` 或替换底图，编辑器约 2 秒内自动重新载入。

## 疑难排解

- **底图读取失败 / Failed to fetch / 只显示一半**：部分防毒网页防护、VPN 或网络过滤驱动会卡住本机的大型二进制传输。
  编辑器已改用 JSON 分段传送底图来避开；若仍失败，请把 `127.0.0.1` 加入防毒 / 广告拦截的白名单，
  详细错误写在 `logs/` 最新的日志里。打包时测试若显示「本机大型二进制传输被卡住」，就是这个情况（不影响使用）。
- **打不开 / 网址无回应**：确认黑色窗口还开着；看启动画面上的「本机网址」（端口可能因占用而改变）。
