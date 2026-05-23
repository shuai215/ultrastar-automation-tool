# UltraStar Clone

[English version](README.md)

UltraStar 歌曲导入助手 — 从 USDB 搜索歌词、下载 UltraStar `.txt` 文件，通过 yt-dlp 转换 YouTube 媒体。

## 功能

- **USDB 搜索** — 按歌手/歌名搜索，支持从结果列表中选择
- **直接 URL** — 跳过搜索，直接用 YouTube 链接下载媒体
- **歌词下载** — 从 USDB 获取 UltraStar `.txt` 歌词文件
- **媒体转换** — yt-dlp 将 YouTube 视频转为 MP3 或 MP4
- **标签编辑** — 自动更新 `#MP3`、`#VIDEO`、`#GAP` 标签
- **本地曲库** — 浏览已下载歌曲，内置播放器同步显示歌词
- **设置持久化** — 主题、输出目录、下载默认值和凭据保存到 `~/.ultrastar_clone/`

## 架构

```
src/ultrastar_clone/
├── models.py               # 共享数据模型 (SongRequest, SongMetadata, ImportResult)
├── cli.py                  # 命令行入口
├── gui_app.py              # GUI 启动脚本
│
├── core/                   # 领域逻辑 (无 GUI 依赖)
│   ├── scraper.py          # USDB 登录、搜索、详情页解析
│   ├── downloader.py       # USDB 歌词下载、等待页处理
│   ├── converter.py        # yt-dlp 媒体下载/转换 (MP3/MP4)
│   ├── editor.py           # UltraStar txt 标签编辑 (#MP3/#VIDEO/#GAP)
│   ├── song_parser.py      # UltraStar txt 文件解析
│   └── playback_timeline.py # 歌词时间轴构建与查询
│
├── services/               # 应用编排 (无 GUI 依赖)
│   ├── controller.py       # 导入流程编排 (搜索→歌词→媒体→标签)
│   ├── settings.py         # 配置路径、凭据/偏好持久化
│   ├── library.py          # 本地曲库扫描
│   └── logger.py           # 日志工厂
│
├── gui/                    # Qt 界面 (QFluentWidgets)
│   ├── app.py              # 入口，向后兼容 re-export
│   ├── main_window.py      # 主窗口，页面导航 + 信号连接
│   ├── home_page.py        # 导入页 (搜索 USDB 或输入 YouTube URL)
│   ├── library_page.py     # 曲库页 (浏览本地歌曲)
│   ├── player_page.py      # 播放器页 (视频/音频 + 歌词同步)
│   ├── settings_page.py    # 设置页 (凭据、主题、导入默认值)
│   ├── log_page.py         # 日志页
│   ├── workers.py          # 后台线程 (ImportWorker, SearchWorker)
│   ├── widgets.py          # 自定义组件 (歌词显示、表格)
│   └── utils.py            # 辅助函数 (无 Qt 依赖)
│
tests/                      # 单元测试 (unittest)
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

四个页面:

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
