# UltraStar Clone — Technical Specification

## 1. 项目概述

一个洁净室实现的 UltraStar 歌曲导入助手。搜索 USDB 歌词库，下载 `.txt` 歌词文件，通过 yt-dlp 转换 YouTube 媒体（MP3/MP4），并提供本地曲库浏览和内建播放器。

## 2. 技术栈

| 层 | 技术 |
|---|------|
| 语言 | Python >= 3.11 |
| GUI 框架 | PyQt6 + QFluentWidgets（Fluent Design 组件库） |
| 媒体播放 | Qt Multimedia（QMediaPlayer + QVideoWidget） |
| 媒体下载 | yt-dlp（子进程调用，非 Python API） |
| 转码 | ffmpeg（由 yt-dlp 内部调用） |
| HTTP 客户端 | stdlib `urllib.request`（无第三方 HTTP 库） |
| HTML 解析 | stdlib `re`（无第三方解析库） |
| 测试 | unittest + pytest |

## 3. 三层架构

```
src/ultrastar_clone/
├── core/          # 纯领域逻辑，无 GUI / 文件系统副作用
├── services/      # 应用编排，无 GUI 依赖
├── gui/           # Qt 表示层
├── models.py      # 共享数据模型
├── cli.py         # CLI 入口
└── gui_app.py     # GUI 启动器
```

### 3.1 core/ — 领域逻辑

每个模块通过 ABC 定义公开契约，测试通过注入 Fake 实现完成。

| 模块 | 职责 | ABC |
|------|------|-----|
| `scraper.py` | USDB 登录、搜索、详情页解析、YouTube URL 提取 | `USDBScraper` |
| `downloader.py` | USDB wait 页面处理、`wd=1` 表单提交、txt 提取 | `USDBDownloader` |
| `converter.py` | yt-dlp 子进程封装、进度流、403/SABR 重试 | `MediaConverter` |
| `editor.py` | UltraStar txt 标签编辑（`#MP3`, `#VIDEO`, `#GAP`）、备份/恢复 | — |
| `song_parser.py` | UltraStar txt 文件解析 → `Song` 数据结构 | — |
| `playback_timeline.py` | BPM → 毫秒时间线转换、播放位置 → 歌词窗口 | — |

### 3.2 services/ — 应用编排

| 模块 | 职责 |
|------|------|
| `controller.py` | `ImportController` 执行完整导入流水线：验证 → 搜索 → 下载歌词 → 转换媒体 → 编辑 txt 标签，通过回调报告进度 |
| `settings.py` | 配置路径（`~/.ultrastar_clone/`）、凭据/偏好/收藏 JSON 持久化 |
| `library.py` | 本地歌曲文件夹扫描（检测 TXT/MP3/MP4 文件完整性） |
| `logger.py` | 文件 + 控制台日志工厂 |

### 3.3 gui/ — Qt 表示层

| 页面 | 类 | 职责 |
|------|-----|------|
| 导入 | `HomePage` | 搜索 USDB 或输入 YouTube URL，启动物理导入 |
| 曲库 | `LibraryPage` | 浏览本地歌曲、收藏/删除、双击播放 |
| 播放器 | `PlayerPage` | 视频/音频播放 + 三行同步歌词显示 |
| 设置 | `SettingsPage` | 凭据、输出目录、导入默认值 |
| 日志 | `LogPage` | 导入活动日志 |
| 主窗口 | `UltraStarFluentWindow` | 页面导航、信号路由、后台线程管理 |

## 4. 数据流

### 4.1 导入流水线

```
HomePage.startRequested
  → SongRequest (dataclass, 输入验证)
  → ImportWorker.run() (后台 QThread)
    → ImportController.import_song()
      → USDBScraper.search()         # 搜索 USDB
      → USDBDownloader.download()    # 下载 txt 歌词
      → MediaConverter.convert()     # yt-dlp 下载/转码媒体
      → Editor.edit_tags()           # 写回 #MP3/#VIDEO/#GAP 标签
      → ImportResult                 # 返回结果
    → worker.done / worker.failed    # 信号回 GUI
```

### 4.2 歌词播放同步

```
parse_ultrastar_txt(txt_path)
  → Song (lyrics: tuple[LyricsLine, ...], bpm, gap_ms)

build_timed_lyrics(song)
  → tuple[TimedLyricsLine, ...] (start_time_ms, end_time_ms, text)

QMediaPlayer.positionChanged(position_ms)
  → lyrics_at_position(timed_lyrics, position_ms)
    → LyricsWindow (previous, current, next)
  → lyric_display_payload(window, position_ms)
    → (previous_text, current_text, next_text)  # ~ 标记已清除
  → LyricDisplayWidget.set_lyrics(prev, cur, next)
```

## 5. 数据模型

### SongRequest (models.py)
- `artist`, `title` — 搜索字段
- `input_mode` — `"search"` | `"url"`
- `download_lyrics`, `download_audio`, `download_video` — 下载开关
- `target_root` — 输出目录（Path）
- `selected_song_id` — 从搜索结果中选择的 USDB song ID

### ImportResult (models.py)
- `song_folder` — 输出目录路径
- `txt_path` — 歌词文件路径（可选）
- `media_paths` — 媒体文件路径列表

### Song / LyricsLine / Note (song_parser.py)
- UltraStar txt 文件的内存表示

### TimedLyricsLine / LyricsWindow (playback_timeline.py)
- 带播放时间戳的歌词行、播放位置上下文窗口

## 6. 持久化

所有数据存于 `~/.ultrastar_clone/`：

| 文件 | 内容 | 格式 |
|------|------|------|
| `credentials.json` | USDB 用户名/密码 | `{"username": "", "password": ""}` |
| `preferences.json` | 主题、输出目录、下载默认值 | `{"theme": "auto", ...}` |
| `favorites.json` | 收藏的歌曲文件夹路径 | `{"folders": [...]}` |

凭据也支持环境变量：`USDB_USER`, `USDB_PASS`（优先级高于文件）。

## 7. 外部依赖

### Python 包
- `PyQt6 >= 6.6` — Qt 绑定
- `PyQt6-Fluent-Widgets >= 1.5` — Fluent Design 组件
- `yt-dlp >= 2025.1` — YouTube 下载器（Python 包，提供 CLI）

### 系统工具（需在 PATH）
- `yt-dlp` — 媒体下载（通过 `subprocess` 调用）
- `ffmpeg` — 音视频转码（由 yt-dlp 内部使用）

## 8. 测试策略

- 框架：`unittest`（stdlib），通过 `pytest` 运行
- 依赖注入：所有外部依赖通过 ABC 注入，测试提供 Fake 实现
- 文件测试：使用 `tempfile.TemporaryDirectory`
- 网络：零网络调用（所有 HTTP 测试使用 Fake）
- 位置：`tests/`，按被测试模块命名
