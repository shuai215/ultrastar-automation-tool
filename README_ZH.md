# UltraStar Clone

[English version](README.md)

UltraStar 歌曲导入助手：从 USDB 搜索歌词、下载 UltraStar `.txt` 文件，并通过 YouTube 链接下载/转换 MP3 或 MP4 媒体。界面使用 PyQt6 + QFluentWidgets。

## 快速开始

发布版面向普通 Windows 用户：

1. 从 Releases 下载 `UltraStar-Clone.exe`。
2. 直接运行 exe。
3. 在 Settings 页面保存 USDB 用户名和密码。

发布版已经打包 Python 运行时、`yt-dlp` Python 包和 `ffmpeg.exe`，不需要额外安装 Python、yt-dlp 或 ffmpeg。

## 功能

- **USDB 搜索** - 按歌手/歌名搜索，并从候选结果中选择。
- **直接 URL** - 粘贴 YouTube 链接，跳过 USDB 搜索下载媒体。
- **歌词下载** - 从 USDB 获取 UltraStar `.txt` 文件。
- **媒体转换** - 使用内置 yt-dlp 包和 ffmpeg 转换 MP3/MP4。
- **标签编辑** - 自动更新 `#MP3`、`#VIDEO`、`#GAP` 等标签。
- **本地曲库** - 浏览、收藏、删除已导入歌曲。
- **内置播放器** - 播放视频/音频，并同步显示歌词。
- **设置持久化** - 保存凭据、输出目录、主题和下载默认值。

## 源码运行

源码开发需要 Python 3.11+：

```powershell
conda create -n new_for_project python=3.11
conda activate new_for_project
pip install -r requirements.txt
```

源码运行时：

- `yt-dlp` 由 `requirements.txt` 安装。
- `ffmpeg.exe` 应放在 `src/ultrastar_clone/bin/ffmpeg.exe`，或者让 `ffmpeg` 位于系统 `PATH`。

### GUI

```powershell
$env:PYTHONPATH = 'D:\GUI_shuai\src'
python -m ultrastar_clone.gui_app
```

### CLI

```powershell
$env:PYTHONPATH = 'D:\GUI_shuai\src'
$env:USDB_USER = 'your_user'
$env:USDB_PASS = 'your_password'

python -m ultrastar_clone.cli --artist 'Coldplay' --title 'Yellow' --output demo_output
python -m ultrastar_clone.cli --mode url --youtube-url 'https://...' --output demo_output --video
python -m ultrastar_clone.cli --artist 'Usher' --title 'U Remind Me' --output demo_output --skip-media
```

## 测试

```powershell
$env:PYTHONPATH = 'D:\GUI_shuai\src'
python -m unittest discover -s tests -v
```

## 打包

```powershell
pyinstaller ultrastar_clone.spec --noconfirm
```

`ultrastar_clone.spec` 会把 `src/ultrastar_clone/bin/ffmpeg.exe` 打进单文件 exe，并在 `dist/` 下生成发布用文件。

## 架构

```text
src/ultrastar_clone/
|-- models.py                # 共享数据模型
|-- cli.py                   # 命令行入口
|-- gui_app.py               # GUI 启动入口
|-- core/                    # 领域逻辑，不依赖 GUI
|   |-- scraper.py           # USDB 登录、搜索、详情页解析
|   |-- downloader.py        # USDB 歌词下载
|   |-- converter.py         # yt-dlp Python API 和 ffmpeg 转换
|   |-- editor.py            # UltraStar txt 标签编辑
|   |-- song_parser.py       # UltraStar txt 解析
|   `-- playback_timeline.py # 歌词时间轴
|-- services/                # 应用编排
|   |-- controller.py        # 导入流程
|   |-- errors.py            # 用户可见错误提示
|   |-- settings.py          # 配置持久化
|   |-- library.py           # 本地曲库扫描
|   `-- logger.py            # 日志
|-- gui/                     # Qt 界面层
|   |-- main_window.py       # 主窗口和信号连接
|   |-- home_page.py         # 导入页面
|   |-- library_page.py      # 曲库页面
|   |-- player_page.py       # 播放器页面
|   |-- settings_page.py     # 设置页面
|   |-- log_page.py          # 日志页面
|   |-- workers.py           # 后台线程
|   `-- widgets.py           # 自定义控件
`-- bin/                     # 打包用本地工具，例如 ffmpeg.exe
```

## 常见问题

- **USDB login failed**：检查 Settings 中的用户名和密码；如果凭据正确，可能是 USDB 临时不可用或登录页面发生变化。
- **Network request failed**：检查网络、VPN/代理、防火墙，然后重试。
- **YouTube download failed**：YouTube 页面或提取规则变化会影响 yt-dlp。源码版可以更新 yt-dlp；发布版需要重新打包 exe。
- **ffmpeg was not found**：发布版应该内置 ffmpeg；请重新下载发布包，或确认源码打包时存在 `src/ultrastar_clone/bin/ffmpeg.exe`。
- **Permission denied**：请选择有写入权限的输出目录，并检查 Windows 安全软件或 Controlled Folder Access 是否拦截。

## 注意

- 不要把 USDB 用户名和密码硬编码到源码里。
- 默认配置保存在 `~/.ultrastar_clone/`。
- Windows 未签名 exe 可能触发 SmartScreen 或杀毒软件提示；发布时可以考虑代码签名。
