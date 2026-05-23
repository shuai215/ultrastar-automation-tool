# UltraStar Clone

UltraStar 歌曲导入助手 — 从 USDB 搜索歌词、下载 UltraStar `.txt` 文件，并通过 yt-dlp 将 YouTube 媒体转换为 MP3/MP4。

An UltraStar song import assistant — search USDB for lyrics, download UltraStar `.txt` files, and convert YouTube media to MP3/MP4 via yt-dlp.

## 功能 / Features

- **USDB 搜索 / Search** — 按歌手/歌名搜索，支持从结果列表中选择 / Search by artist/title, select from result list
- **直接 URL / Direct URL** — 跳过搜索，直接用 YouTube 链接下载媒体 / Skip search, download media directly from a YouTube link
- **歌词下载 / Lyrics** — 从 USDB 获取 UltraStar `.txt` 歌词文件 / Fetch `.txt` lyric files from USDB
- **媒体转换 / Media** — yt-dlp 下载 YouTube 视频并转为 MP3 或 MP4 / Download and convert YouTube videos to MP3/MP4
- **标签编辑 / Tag editing** — 自动更新 `#MP3`、`#VIDEO`、`#GAP` 标签 / Auto-update UltraStar tags
- **本地曲库 / Library** — 扫描已下载歌曲，内置播放器预览 / Scan local songs and preview with built-in player
- **设置持久化 / Persistence** — 主题、输出目录、下载选项和凭据保存到 `~/.ultrastar_clone/` / Theme, output folder, download defaults, and credentials saved locally

## 项目结构 / Structure

```
src/ultrastar_clone/
├── core/           # 领域逻辑 / domain logic (scraper, downloader, converter, editor, parser, playback)
├── services/       # 应用编排 / orchestration (controller, settings, library, logger)
├── gui/            # Qt 界面 / Qt UI (app.py)
├── models.py       # 共享数据模型 / shared data models
├── cli.py          # 命令行入口 / CLI entry
└── gui_app.py      # GUI 启动入口 / GUI launcher
tests/              # 单元测试 / unit tests (unittest)
```

## 快速开始 / Quick Start

### 安装 / Install

```powershell
pip install -e ".[dev]"
```

外部依赖 / External tools (需在 PATH 中 / required on PATH): `yt-dlp`, `ffmpeg`

### CLI

```powershell
$env:PYTHONPATH='D:\GUI_shuai\src'
$env:USDB_USER='your_user'
$env:USDB_PASS='your_password'

# 搜索模式 / Search mode
python -m ultrastar_clone.cli --artist 'Coldplay' --title 'Yellow' --output demo_output

# 直接 URL 模式 / Direct URL mode
python -m ultrastar_clone.cli --mode url --youtube-url 'https://...' --output demo_output --video

# 仅下载歌词 / Lyrics only
python -m ultrastar_clone.cli --artist 'Usher' --title 'U Remind Me' --output demo_output --skip-media
```

### GUI

```powershell
$env:PYTHONPATH='D:\GUI_shuai\src'
$env:USDB_USER='your_user'
$env:USDB_PASS='your_password'
python -m ultrastar_clone.gui_app
```

GUI 包含四个页面 / Four pages:

| 页面 / Page | 功能 / Function |
|-------------|-----------------|
| **Import** | 搜索歌曲或输入 YouTube URL，一键导入 / Search or paste YouTube URL, one-click import |
| **Library** | 浏览本地曲库，双击播放 / Browse local songs, double-click to play |
| **Settings** | 主题、输出目录、下载默认值、USDB 凭据 / Theme, output folder, download defaults, credentials |
| **Log** | 查看导入日志 / View import logs |

## 运行测试 / Tests

```powershell
$env:PYTHONPATH='D:\GUI_shuai\src'
python -m unittest discover -s tests -v
```

## 注意事项 / Notes

- USDB 凭据通过环境变量或设置页面输入，**不要硬编码在源码中** / Credentials via env vars or settings page — **never hardcode them**
- 导入的歌曲默认保存到 UltraStar 标准歌曲目录，可在设置中自定义 / Songs save to the standard UltraStar song directory by default; customize in Settings
