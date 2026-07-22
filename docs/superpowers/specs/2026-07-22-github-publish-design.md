# joycon-vibe-keyboard GitHub 发布整理 - 设计文档

> 2026-07-22 | 范围：打包发布 + 修一致性 + README 优化，不重构代码

## 背景

joycon-vibe-keyboard 试用稳定（按键已好 用），准备提交 GitHub。当前代码能跑，但存在两类问题：

1. **文档一致性偏差**：7-22 把 SR 从普通按键 `v` 改成按住修饰键 `alt_r`（唤醒 SaySo），但 README / DESIGN / keymap.html / joycon_config.html 仍展示旧映射；端口号 README 写 8765、实际代码是 8766。
2. **非 git 仓库**：无版本管理，无 .gitignore，status.json 等运行时文件混在目录里。

## 决策（用户已确认）

| 项 | 决策 |
|----|------|
| Repo 归属 | MagnetQ 组织，private |
| 优化范围 | 中等：打包 + 修一致性 + README 优化，**代码逻辑不动** |
| README 语言 | 保持英文（DESIGN.md 保持中文） |
| 两张大 PNG | 都保留进 repo |

## 目录结构方案

**方案 A（推荐）：平铺 + 清理，不移动文件**

- 根目录保持现状（代码、配置、HTML、文档、图都在根）
- 删 `diag_hid.py`（本次调试临时文件）、`debug_stick.py`（Y 轴已确认死亡，工具使命完成）
- 保留 `test_buttons.py`（副厂手柄按键发现工具，未来换手柄可能复用）
- 加 `.gitignore` 排除运行时文件

理由：`joycon_config.html` 和 `keymap.html` 被 `config_server.py` / 用户直接打开引用，移动会引入路径风险；用户选了"代码不动"，平铺清理风险最低。

**方案 B（不推荐）：轻分组**（调试脚本移 `tools/`、图移 `docs/images/`）--要同步 config_server 的 HTML 引用路径和 README 结构说明，改动面扩大，违背"代码不动"。

## 一致性修复清单

| 文件 | 位置 | 问题 | 修复 |
|------|------|------|------|
| `README.md` | L94, L121 | 端口写 8765 | 改 8766 |
| `README.md` | L42 | 硬编码 `~/Documents/workspace-ai/code/joycon-vibe-keyboard` | 改通用 `cd joycon-vibe-keyboard` |
| `README.md` | L100, L111 | R=Typeless ✅；SR 写 `v`/⌘+V paste ❌ | SR 改 `alt_r`/唤醒 SaySo |
| `README.md` | L22 | "macOS 15 Sequoia" | 更新为 macOS 26 Tahoe（Darwin 25.5） |
| `README.md` | L115-128 | Project Structure | 同步：加 `joycon_watchdog.py`、删 `debug_stick.py`、保留 `test_buttons.py` |
| `README.md` | L96-113 | Default Mappings 表 SR 行 | 更新为「SR (hold) | Right ⌥ | Hold to trigger SaySo voice」 |
| `README.md` | L138-144 | Known Limitations | 加：SaySo 需辅助功能权限；网页配置页 SR 展示待同步 |
| `joycon_mapper.py` | L19 docstring | 端口写 8765 | 改 8766（**仅注释，无逻辑改动**） |
| `DESIGN.md` | L220 | SR 写 `v`/⌘+V 粘贴 | 改 alt_r/唤醒 SaySo |
| `keymap.html` | L226-229 | 硬编码 `R + SR = ⌘V 粘贴` | 改「SR 按住 -> 右 Option（唤醒 SaySo）」；核对其他按键与 config.json 一致 |

## joycon_config.html SR 同步（待用户定，默认不做）

`joycon_config.html` 把 SR 归在「侧键/press」普通按键区（L438），note 写「粘贴」（L454），而 config.json 里 SR 是 modifiers。**不同步的风险**：用户在网页配置页保存时，SR 可能被当普通按键写回，覆盖 `alt_r`。

- **选项 1（默认，符合"代码不动"）**：本次不同步，在 README Known Limitations 记「网页配置页 SR 暂按普通按键展示，建议直接编辑 config.json 或保存后检查 SR」，并把"同步 SR 展示"列入项目壳待办。
- **选项 2**：本次同步（把 SR 从 press 区移到 hold 区 + 改 note），超出"代码不动"但消除覆盖风险。

## README 重写要点（英文，中等范围）

保留现有结构（Why / Features / Requirements / Installation / Quick Start / Configuration / Web Config UI / Default Mappings / Project Structure / How It Works / Known Limitations / License），重点改：

- **Quick Start**：去硬编码路径，用 `cd joycon-vibe-keyboard && python3 joycon_mapper.py`
- **Features**：加「Bluetooth watchdog」(optional blueutil reconnect)、「SR hold-to-talk for SaySo」
- **Default Mappings**：SR 行更新；R 保持 Typeless
- **Project Structure**：同步实际文件清单
- **Known Limitations**：加 SaySo 辅助功能权限、副厂 Y 轴、网页 SR 展示待同步
- **License**：保持 "Personal use project. No license."（private repo）

## .gitignore

```
# 运行时状态（mapper/watchdog 写）
status.json

# Python
__pycache__/
*.pyc

# macOS
.DS_Store

# 日志
*.log
```

## git 发布步骤

1. 删 `diag_hid.py`、`debug_stick.py`
2. 建 `.gitignore`
3. 执行一致性修复（README / mapper docstring / DESIGN / keymap.html）
4. 建 `docs/superpowers/specs/` 放本 spec
5. `git init`
6. `git add .`（.gitignore 已排除 status.json）
7. `git commit -m "Initial commit: Joy-Con (R) vibe coding keyboard mapper"`
8. `gh repo create MagnetQ/joycon-vibe-keyboard --private --source=. --push`

## 实施步骤（顺序）

1. 删 `diag_hid.py`、`debug_stick.py`
2. 写 `.gitignore`
3. 改 `joycon_mapper.py` L19 docstring 端口
4. 改 `DESIGN.md` L220 SR 行
5. 改 `keymap.html` L226-229 SR 展示（+ 核对其他按键）
6. 重写 `README.md`（一致性 + 结构优化）
7. 建 `docs/superpowers/specs/2026-07-22-github-publish-design.md`（本文件）
8. `git init` + add + commit
9. `gh repo create MagnetQ/joycon-vibe-keyboard --private --source=. --push`
10. 更新工作台 `projects/joycon-vibe-keyboard.md`（状态改"已建 MagnetQ private repo"，记 URL）
11. 更新 `logs/2026-07-22.md` 补本次条目

## 不做（YAGNI）

- 不重构 mapper / watchdog 代码（用户选"代码不动"）
- 不改 config.json（当前 SR=alt_r 正确）
- 不加 CI / 测试框架（个人项目，超范围）
- 不加多语言 README（保持英文）
- 不动 HTML 文件结构（防路径引用断裂）
