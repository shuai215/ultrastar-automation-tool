# UltraStar Clone

[English version](README_EN.md)

UltraStar 歌曲导入助手 — 从 USDB 搜索歌词、下载 UltraStar `.txt` 文件，并通过 yt-dlp 将 YouTube 媒体转换为 MP3/MP4。

## 功能

- **USDB 搜索** — 按歌手/歌名搜索，支持从结果列表中选择
- **直接 URL** — 跳过搜索，直接用 YouTube 链接下载媒体
- **歌词下载** — 从 USDB 获取 UltraStar `.txt` 歌词文件
- **媒体转换** — yt-dlp 下载 YouTube 视频并转为 MP3 或 MP4
- **标签编辑** — 自动更新 `#MP3`、`#VIDEO`、`#GAP` 标签
- **本地曲库** — 扫描已下载歌曲，内置播放器预览
- **设置持久化** — 主题、输出目录、下载选项和凭据保存到 `~/.ultrastar_clone/`

## 项目结构

```
src/ultrastar_clone/
├── core/           # 领域逻辑 (scraper, downloader, converter, editor, parser, playback)
├── services/       # 应用编排 (controller, settings, library, logger)
├── gui/            # Qt 界面 (app.py)
├── models.py       # 共享数据模型
├── cli.py          # 命令行入口
└── gui_app.py      # GUI 启动入口
tests/              # 单元测试 (unittest)
```

## 快速开始

### 安装

```powershell
pip install -e ".[dev]"
```

外部依赖 (需在 PATH 中): `yt-dlp`, `ffmpeg`

### CLI

```powershell
$env:PYTHONPATH='D:\GUI_shuai\src'
$env:USDB_USER='your_user'
$env:USDB_PASS='your_password'

# 搜索模式
python -m ultrastar_clone.cli --artist 'Coldplay' --title 'Yellow' --output demo_output

# 直接 URL 模式
python -m ultrastar_clone.cli --mode url --youtube-url 'https://...' --output demo_output --video

# 仅下载歌词
python -m ultrastar_clone.cli --artist 'Usher' --title 'U Remind Me' --output demo_output --skip-media
```

### GUI

```powershell
$env:PYTHONPATH='D:\GUI_shuai\src'
$env:USDB_USER='your_user'
$env:USDB_PASS='your_password'
python -m ultrastar_clone.gui_app
```

GUI 包含四个页面:

| 页面 | 功能 |
|------|------|
| **Import** | 搜索歌曲或输入 YouTube URL，一键导入 |
| **Library** | 浏览本地曲库，双击播放 |
| **Settings** | 主题、输出目录、下载默认值、USDB 凭据 |
| **Log** | 查看导入日志 |

## 运行测试

```powershell
$env:PYTHONPATH='D:\GUI_shuai\src'
python -m unittest discover -s tests -v
```

## 注意事项

- USDB 凭据通过环境变量或设置页面输入，**不要硬编码在源码中**
- 导入的歌曲默认保存到 UltraStar 标准歌曲目录，可在设置中自定义
