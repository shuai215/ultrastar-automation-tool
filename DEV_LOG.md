# Development Log

## 2026-05-25 - 歌词滚动系统重构与调试记录

### 1. 初始目标

最初目标是优化播放器中的歌词显示系统。

原来的实现方式是使用 3 个固定 `QLabel`：

- 上一行歌词
- 当前行歌词
- 下一行歌词

当播放位置变化时，程序直接替换这三个 label 的文字。这个方案功能上可用，但视觉上不够平滑，歌词切换更像是“突然换字”，而不是自然滚动。

期望效果：

- 只显示三行歌词。
- 当前歌词行稳定居中。
- 播放到下一句歌词时，歌词区域平滑上滑一次。
- 视频窗口大小、位置和比例保持不变。
- 歌词窗口放在视频下方空白区域中，而不是整个界面的正中心。

这次任务的核心不是重做播放器，而是修正歌词显示层。

### 2. 原始方案：三行 QLabel 替换文字

原始结构大致是：

```text
LyricDisplayWidget
├── previous QLabel
├── current QLabel
└── next QLabel
```

每次当前歌词 index 变化时，就更新这三个 label 的文字。

问题：

- 歌词是被替换的，不是被滚动的。
- 歌词切换没有真实位移动画。
- 视觉上有明显停顿和闪动。
- 逻辑被限制在 previous/current/next 三行结构里，后续很难做自然滚动效果。

因此模型需要从“替换三行文字”改成“整首歌词作为一条竖向 strip 滚动”。

### 3. 被否决方案：Continuous Flow 连续流动

第一次尝试的方向是 Continuous Flow，也就是连续流动模型。

核心思路：

- 把整首歌词预先渲染成一条垂直 strip。
- 根据播放时间计算一个连续的小数 index。
- 以高频率连续移动整条歌词 strip。

核心公式：

```text
float_index = 当前歌词行 index + 到下一句歌词的进度
```

例如：

```text
第 0 行开始时间: 0 ms
第 1 行开始时间: 3000 ms

pos = 1000 ms -> float_index = 0.33
pos = 2000 ms -> float_index = 0.67
pos = 3000 ms -> float_index = 1.00
```

这个方案会让歌词在两句歌词之间持续向上移动。

它后来被否决，因为当前句正在播放时，当前歌词应该稳定居中。只有当播放位置到达下一句歌词的 start time 时，才应该触发一次平滑上滑动画。

错误效果：

- 当前句还在唱，歌词已经慢慢往下一句移动。

正确效果：

- 当前句保持居中。
- 播放到下一句 start time。
- 歌词 strip 平滑上滑一次。
- 下一句歌词居中。

### 4. 最终交互模型：Triggered Smooth Scroll

第二次改成了正确模型：Triggered Smooth Scroll。

核心逻辑：

- 不在两句歌词之间持续插值滚动。
- 播放位置只用于判断当前 `target_index`。
- 只有 `target_index` 变化时，才触发一次滚动动画。

逻辑从：

```text
播放位置 -> float_index -> 持续移动
```

改成：

```text
播放位置 -> 当前歌词 target_index -> 如果 index 变化，则触发动画
```

新的结构：

```text
viewport
└── lyric_strip
    ├── QLabel 第 0 行
    ├── QLabel 第 1 行
    ├── QLabel 第 2 行
    ├── QLabel 第 3 行
    └── ...
```

所有歌词一次性渲染成一整条竖向 strip。不再每次替换三行文字，而是通过移动整条 strip 来实现滚动效果。

目标效果：

- 当前歌词行居中。
- 播放位置越过下一句歌词开始时间。
- `target_index` 改变。
- `QPropertyAnimation` 把歌词 strip 滚动到新位置。
- 新的当前歌词行居中。

这个方案解决了歌词逻辑层面的核心问题。

### 5. 裁剪机制：从普通 QWidget 改为 QScrollArea

整首歌词 strip 会包含所有歌词行，但视觉上只应该露出三行。

早期使用普通 `QWidget` 作为 viewport 时，裁剪不稳定，歌词可能溢出到视频区域后面。曾尝试使用 Qt 的 child clipping 属性，但当前 PyQt6 环境里对应属性不可用，导致程序崩溃。

最终解决方案是把普通 viewport 替换为 `QScrollArea`：

```text
QScrollArea
└── lyric_strip
    ├── QLabel 第 0 行
    ├── QLabel 第 1 行
    ├── QLabel 第 2 行
    └── ...
```

`QScrollArea` 自带可靠的 viewport 裁剪机制，适合“内容很长，但只显示一小块”的场景。

动画目标也随之改变：

- 旧方案：动画移动 `lyric_strip.pos()`。
- 新方案：动画移动 `verticalScrollBar().value`。

歌词逻辑没有变，仍然是到点触发滚动。变化的是显示和裁剪机制。

这样可以稳定保证：

- 只显示三行歌词。
- viewport 外的歌词被裁剪。
- 歌词不会溢出到视频后面。

### 6. 几何问题：viewport 高度和行高计算不稳定

改成整首歌词 strip 后，接下来遇到的是几何计算问题。

早期版本用 `QLabel.sizeHint()` 来推算歌词行高。这会导致不稳定。

影响真实 label 高度的因素包括：

- 歌词长短不同。
- 是否换行。
- 当前行字体是否更大/更粗。
- `QLabel` 自身 padding。
- Qt layout 的自动计算。

如果滚动位置依赖 label 自己计算出的高度，就可能出现误差累积。

例如代码认为：

```text
每行高度 = 52 px
第 10 行位置 = 10 * 52 = 520 px
```

但实际渲染中每行可能略有差异：

```text
第 0 行 51 px
第 1 行 54 px
第 2 行 50 px
...
```

滚到后面时，当前行就可能偏离中心，表现为“高亮歌词越跑越高”。

解决方法是固定滚动几何：

- 固定行高。
- 固定三行 viewport 高度。
- 固定滚动公式。

早期固定为：

```text
row_height = 52 px
viewport_height = 52 * 3 = 156 px
```

后续因为视觉间距过大，调整为：

```text
row_height = 34 px
visible_lines = 3
viewport_height = 102 px
```

关键原则：

- 每一行的位置由固定 row index 计算。
- `QLabel` 的真实高度不再参与滚动坐标计算。

### 7. 重复加载问题：layout item 残留

之后发现 `set_lines()` 重复执行时，布局会越来越不准。

原因是旧逻辑在重新加载歌词时，只清理了 label，但没有彻底清理 layout 里的所有 item。一些旧的 stretch、spacer 或 layout item 可能残留。

后果：

- 每次 `set_lines()` 后 layout item 越积越多。
- 歌词 strip 高度越来越异常。
- 滚动坐标逐渐不准。

修复方式：

- 每次重建歌词前，彻底清空 layout。
- 不仅删除 `QLabel`，也删除 stretch、spacer 和旧 layout item。
- 然后重新创建歌词 strip。

同时加入回归测试，确保重复调用 `set_lines()` 不会累积 layout item。

### 8. 初始化问题：歌词偏左

换成 `QScrollArea` 后，又出现了初始化时歌词 strip 偏左的问题。

现象：

- 初次打开播放器时歌词偏左。
- 手动缩放窗口后歌词自动居中。

原因：

- `set_lines()` 执行时，`QScrollArea.viewport()` 还没有拿到最终真实宽度。
- strip 是按照一个临时宽度布局的。
- 窗口首次 show 后，viewport 宽度发生变化，但 strip 没有同步重新定位。
- 手动缩放窗口时才触发重新同步。

修复方式：

- 给 `QScrollArea.viewport()` 添加 resize event filter。
- 当 viewport 尺寸变化时，重新调用 `_position_strip()`。

新增测试覆盖：

- 首次 show 后，strip 宽度跟随 viewport 宽度变化。

### 9. 视觉问题：行高太大，像有空行

固定行高解决了滚动稳定性，但最初的 `52px` 太大。

当时：

```text
row_height = 52 px
viewport_height = 156 px
```

视觉效果是歌词之间像有空行，三行歌词区域也太高，同时把底部 Pause 按钮和进度条挤到了页面下方。

后来改成：

```text
row_height = 34 px
viewport_height = 102 px
```

效果：

- 仍然只显示三行。
- 当前行仍然能居中。
- 歌词间距不再过大。
- 底部控制栏保留在视野内。

新增测试确保歌词行高保持紧凑，避免以后又被改回过大的高度。

### 10. 页面布局问题：歌词上下 stretch 挤走 controls

歌词滚动逻辑修好后，接下来出现的是页面布局问题。

播放器的视频区域本身已经固定：

- 视频窗口大小固定。
- 视频窗口位置固定。
- 视频比例固定。

歌词应该放在视频下方的空白区域中间，而不是整个播放器页面的正中心。

第一次修布局时，在歌词 widget 上下加了 stretch：

```text
player row
stretch
lyric display
stretch
controls
```

这确实让歌词更接近中间，但后来带来新问题：底部 Pause 按钮和进度条被挤到了下面。

真正需求：

- 不改变视频区域。
- 歌词 widget 只占三行高度。
- 歌词 widget 放在视频下方空间内。
- 不要让歌词 widget 或 stretch 挤压底部 controls。

最终修复：

- 移除歌词上下多余 stretch。
- 收紧 player page 的 margin 和 spacing。
- 略微降低播放器最小高度。
- 让歌词紧凑地放在视频下方。
- 保证底部 controls 保持可见。

新增测试确保 `PlayerPage` 不再使用会把 controls 挤走的上下 stretch。

### 11. 最终稳定方案

最终采用：

```text
Triggered Smooth Scroll + 整首歌词 strip + QScrollArea 裁剪
```

最终行为：

- 整首歌词预先渲染成一条竖向 strip。
- `QScrollArea` 只显示固定三行高度。
- 当前歌词行稳定居中。
- 播放到下一句 start time 时，滚动条动画滚动一次。
- 下一句歌词居中。
- 视频区域不改变。
- 歌词位于视频下方。
- 底部 controls 保持可见。

最终结构：

```text
LyricDisplayWidget
└── QScrollArea（三行固定高度）
    └── lyric_strip
        ├── QLabel 第 0 行
        ├── QLabel 第 1 行
        ├── QLabel 第 2 行
        ├── QLabel 第 3 行
        └── ...
```

最终滚动逻辑：

```text
播放位置
↓
lyric_target_index()
↓
如果 target_index 变化：
    animate QScrollArea.verticalScrollBar().value
```

最终几何逻辑：

```text
fixed row_height = 34 px
visible_lines = 3
viewport_height = 102 px
scroll_position = f(current_index, row_height)
```

### 12. 职责分层

这次问题表面上是歌词显示问题，本质上是：

```text
时间逻辑 + 几何布局 + 裁剪机制
```

三者同时作用的问题。

最终拆成三层后，结构更清晰：

- `playback_timeline.py`：根据播放时间判断当前歌词 index。
- `LyricDisplayWidget`：渲染整首歌词 strip，并处理滚动动画和裁剪。
- `PlayerPage`：把歌词 widget 放在视频下方正确的位置，并保留底部 controls。

这次最大的工程经验是：歌词系统不是简单的文本显示问题，而是一个时间驱动的 UI 几何系统。

最终方案把“当前歌词是谁”和“歌词如何显示”分离开：

- 时间逻辑决定 `target_index`。
- 显示逻辑负责滚动和裁剪。
- 页面布局只负责摆放位置。

这样后续再修改字体、间距、动画速度或歌词样式时，不容易破坏核心滚动逻辑。

### 13. 新增测试

新增回归测试覆盖：

- 三行 viewport 高度固定。
- 滚动坐标基于固定行高。
- 重复 `set_lines()` 不累积 layout item。
- 首次 show 后 strip 宽度跟随 viewport。
- 歌词行高保持紧凑。
- `PlayerPage` 不使用会挤走 controls 的上下 stretch。

验证命令：

```powershell
$env:PYTHONPATH='D:\GUI_shuai\src'
& 'D:\python\envs\new_for_project\python.exe' -m unittest discover -s tests
```

当前完整测试结果：

```text
Ran 75 tests
OK
```

### 14. 最终结果对比

相比最初的三行 `QLabel` 替换方案：

- 旧方案：直接替换 previous/current/next 三行文字。
- 新方案：整首歌词预渲染，只裁剪显示三行，到点触发平滑滚动。

相比被否决的 Continuous Flow 方案：

- 被否决方案：歌词在两句之间持续移动。
- 最终方案：当前句播放时歌词保持静止，到下一句开始时平滑滚动一次。

相比早期 `QScrollArea` 方案：

- 早期问题：几何不稳定、初始化宽度不同步、行距过大、controls 被挤走。
- 最终方案：固定紧凑行高、viewport resize 后重新定位、滚动位置稳定、页面布局紧凑、controls 保持可见。

### 15. 当前剩余风险和 TODO

当前已知取舍：

- 长歌词可能被裁剪。

这是固定行高带来的代价，但这是有意保留的设计选择。歌词滚动系统最重要的是：

- 滚动坐标稳定。
- 当前行准确居中。
- 只显示三行。

后续可以考虑：

- 方案 1：长歌词自动缩小字号。
- 方案 2：长歌词单行省略号。
- 方案 3：允许固定高度内两行显示。
- 方案 4：根据歌词长度动态缩放文字，但不改变 `row_height`。

关键原则：

- 不能再让 `QLabel` 的真实高度参与滚动坐标计算。
- 否则当前行居中偏移的问题可能重新出现。
