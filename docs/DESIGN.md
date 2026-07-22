# Joy-Con Vibe Coding — 映射配置工具设计文档

## 项目概述

用 Joy-Con (R) 手柄作为 Vibe Coding 的快捷键盘，通过蓝牙 HID 读取手柄按键，映射为键盘快捷键。本工具提供一个浏览器可视化界面，让用户自由配置按键映射关系，支持单键、组合键和摇杆方向映射。

## 系统架构

```
┌─────────────────┐    读写     ┌──────────────┐
│  浏览器配置页面   │ ────────── │  config.json  │
│ joycon_config    │   HTTP API │              │
│   .html          │            └──────┬───────┘
└────────┬────────┘                    │ 启动时读取
         │                             ▼
         │ 托管页面           ┌──────────────────┐
         ▼                   │  joycon_mapper.py │
┌─────────────────┐          │  (蓝牙 HID 读取   │
│ config_server.py │          │   + 键盘模拟)     │
│ (本地 HTTP 服务)  │          └──────────────────┘
└─────────────────┘
```

**四个文件的职责**：

| 文件 | 角色 | 说明 |
|------|------|------|
| `config.json` | 配置源 | 唯一的数据源，JSON 格式，存放所有按键映射 |
| `config_server.py` | 服务器 | Python HTTP 服务器（端口 8766），提供 API + 托管 HTML |
| `joycon_config.html` | 前端 UI | 交互式配置页面，SVG 手柄示意图 + 下拉菜单 |
| `joycon_mapper.py` | 运行时 | 启动时从 config.json 加载映射，通过蓝牙 HID 读取按键并模拟键盘 |

## config.json 格式规范

```json
{
  "modifiers": {
    "R": ["cmd_r"],
    "ZR": ["cmd_r", "alt_r"]
  },
  "buttons": {
    "A": {"modifiers": [], "key": "enter"},
    "B": {"modifiers": ["cmd"], "key": "z"},
    "X": {"modifiers": [], "key": "backspace"}
  },
  "stick": {
    "left": "up",
    "right": "down"
  }
}
```

**三个配置区**：

- `modifiers` — 修饰键（按住生效）。key 是手柄按钮名（R / ZR），value 是键盘修饰键名数组。按住 R 时，所有普通按键自动叠加该修饰键。
- `buttons` — 动作按键（按下即触发）。每个按键包含两个字段：`modifiers`（可选的组合键前缀，空数组表示无）和 `key`（主键）。mapper 根据 modifiers 是否为空自动区分"普通按键"和"组合键"。
- `stick` — 摇杆方向映射。key 是物理方向（left / right），value 是键盘方向键。

**按键名称规范**：

- 特殊键：`enter`、`tab`、`esc`、`backspace`、`delete`、`space`、`up`、`down`、`left`、`right`
- 修饰键：`cmd`、`cmd_l`、`cmd_r`、`alt`、`alt_l`、`alt_r`、`ctrl`、`ctrl_l`、`ctrl_r`、`shift`、`shift_l`、`shift_r`
- 功能键：`f1` ~ `f12`
- 字母/数字：直接用字符，如 `"a"`、`"z"`、`"1"`

## config_server.py 设计

**技术选型**：Python 内置 `http.server`，零外部依赖。

**端口**：8766

**API 接口**：

| 方法 | 路径 | 说明 |
|------|------|------|
| `GET /` | `/` | 返回 joycon_config.html 页面 |
| `GET /api/config` | `/api/config` | 返回当前 config.json 内容（JSON） |
| `POST /api/config` | `/api/config` | 接收 JSON body，写入 config.json |

**启动命令**：

```bash
cd ~/Documents/workspace-ai/code/joycon-vibe-keyboard
python3 config_server.py
# 浏览器打开 http://localhost:8766
```

## joycon_config.html 页面设计

### 整体布局

```
┌──────────────────────────────────────────────────────────┐
│  Joy-Con (R) 按键映射配置                          [保存]  │
├───────────────────────┬──────────────────────────────────┤
│                       │                                  │
│    ┌─────────┐        │  ── 修饰键（按住生效）──          │
│    │         │        │  R  按住触发: [右 Command ▾]      │
│    │  SVG    │        │  ZR 按住触发: [右 Cmd + 右 Opt ▾] │
│    │  Joy-Con│        │                                  │
│    │  (R)    │        │  ── 动作按键（按下触发）──         │
│    │  示意图  │        │  A  [无 ▾]  +  [Enter ▾]         │
│    │         │        │  B  [⌘ ▾]   +  [z ▾]            │
│    │  标注了  │        │  X  [无 ▾]  +  [Backspace ▾]     │
│    │  每个按钮 │        │  Y  [无 ▾]  +  [Escape ▾]       │
│    │  的位置  │        │  ...                             │
│    │         │        │                                  │
│    └─────────┘        │  ── 摇杆方向 ──                   │
│                       │  推左: [↑ ▾]   推右: [↓ ▾]       │
│                       │                                  │
└───────────────────────┴──────────────────────────────────┘
```

### 视觉风格

- 深色主题（`#1a1a2e` 背景，`#e0e0e0` 文字），与 keymap.html 一致
- 左侧 SVG 示意图：Joy-Con (R) 的轮廓，按钮位置标注名称，悬停时高亮
- 右侧配置区：按"修饰键"、"动作按键"、"摇杆"三个分组
- 每个动作按键一行，两个下拉菜单并排：修饰键下拉 + 主键下拉
- 保存按钮右上角，点击后底部弹 toast 提示"保存成功"或"保存失败"

### 下拉菜单选项

**修饰键下拉**（动作按键左侧）：

| 显示 | 值 |
|------|------|
| 无 | `[]` |
| ⌘ | `["cmd"]` |
| ⌘+⇧ | `["cmd", "shift"]` |
| ⌘+⌥ | `["cmd", "alt"]` |
| ⇧ | `["shift"]` |
| ⌥ | `["alt"]` |
| ⌃ | `["ctrl"]` |
| ⌘+⌃ | `["cmd", "ctrl"]` |

**主键下拉**（动作按键右侧）：

Enter、Tab、Escape、Backspace、Delete、Space、↑ ↓ ← →、A–Z、0–9、F1–F12

**修饰键按住触发下拉**（R / ZR 专用）：

右 Command、右 Command + 右 Option、右 Option、右 Shift、无

**摇杆方向下拉**：

↑、↓、←、→、无

### 交互行为

- 页面加载时，`GET /api/config` 获取当前配置并填充所有下拉菜单
- 用户修改任意下拉后，点击"保存"按钮，`POST /api/config` 提交整个配置
- 保存成功：底部绿色 toast "保存成功，重启 mapper 后生效"
- 保存失败：底部红色 toast "保存失败: {错误信息}"
- 不做实时保存，避免用户改到一半就写入不完整配置

## joycon_mapper.py 改造

**改造要点**：删除所有硬编码的 MODIFIERS / BUTTONS / COMBOS 字典，改为启动时从 config.json 加载。

**新增 `load_config()` 函数**：

1. 读取 config.json
2. 将字符串键名转换为 pynput 的 `Key` 或 `KeyCode` 对象
3. 根据 `buttons` 中每个按键的 `modifiers` 是否为空，自动拆分为"普通按键"和"组合键"
4. 返回 `(modifiers, buttons, combos, stick)` 四个字典

**键名转换规则**：

```python
SPECIAL_KEYS = {
    "enter": Key.enter, "tab": Key.tab, "esc": Key.esc,
    "backspace": Key.backspace, "cmd": Key.cmd, ...
}

def resolve_key(name):
    if name in SPECIAL_KEYS: return SPECIAL_KEYS[name]
    if len(name) == 1: return KeyCode.from_char(name)
    return getattr(Key, name)
```

**启动日志**：打印当前加载的所有映射关系，方便用户确认配置已生效。

**其他不变**：蓝牙 HID 读取逻辑、自动重连、摇杆处理等保持原样。

## 使用流程

```
第一次使用：
  1. 终端: python3 config_server.py
  2. 浏览器: http://localhost:8766
  3. 在页面上配置按键映射，点保存
  4. 终端: python3 joycon_mapper.py
  5. 开始用 Joy-Con 操作

修改配置：
  1. 停止 joycon_mapper.py（Ctrl+C）
  2. 浏览器打开配置页面，改映射，保存
  3. 重启 joycon_mapper.py

日常启动：
  1. python3 joycon_mapper.py（直接读取上次的 config.json）
```

## 当前默认映射

| 手柄按键 | 键盘映射 | Vibe Coding 用途 |
|---------|---------|-----------------|
| R（按住） | 右 Command | 触发 Typeless 语音输入 |
| ZR（按住） | 右 Cmd + 右 Opt | 备用组合修饰键 |
| A | Enter | 确认 / 发送 |
| B | ⌘+Z | 撤销 |
| X | Backspace | 删除 |
| Y | Escape | 取消 / 退出 |
| PLUS | Tab | 接受 AI 补全建议 |
| MINUS | a | 配合 R 键 = ⌘+A 全选 |
| HOME | s | 配合 R 键 = ⌘+S 保存 |
| STICK_CLICK | d | 配合 R 键 = ⌘+D |
| SL | c | 配合 R 键 = ⌘+C 复制 |
| SR（按住） | 右 Option（alt_r） | 按住唤醒 SaySo 语音输入 |
| 摇杆左 | ↑ | 向上移动（选代码建议） |
| 摇杆右 | ↓ | 向下移动（选代码建议） |

## 已知限制

- Joy-Con Y 轴物理损坏（第三方手柄），摇杆仅 X 轴可用，左右映射为上下方向
- macOS 下同一时间只能有一个进程打开 HID 设备，mapper 运行时其他调试脚本无法连接
- 修改配置后需要重启 mapper 才能生效（不做热加载）
- 蓝牙连接约 5 秒无数据视为断开，自动重连
