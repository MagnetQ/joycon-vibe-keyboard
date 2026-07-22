# Joy-Con Vibe Keyboard

Use a Nintendo Joy-Con (R) controller as a shortcut keyboard for vibe coding with AI tools like Claude Code, Cursor, and Codex. Maps Bluetooth HID button presses to keyboard events via a lightweight Python script - no Steam, no Karabiner, no daemon overhead.

## Why

When vibe coding, you spend a lot of time accepting suggestions, undoing, navigating options, and triggering voice input. A Joy-Con in your hand gives you physical, tactile shortcuts without reaching for the keyboard. The idea is simple: hold a shoulder button as a modifier (like ⌘), then tap face buttons for common actions.

This project was born out of frustration with existing mapping tools - Enjoyable locks up when the Joy-Con gyroscope fires, Steam causes the MacBook to overheat, and Karabiner can't read Bluetooth HID gamepads. A 200-line Python script turned out to be the most reliable solution.

## Features

- **Hold-modifier buttons** - R and ZR act as modifier keys (Right Command, Right Option) that you hold down while pressing other buttons
- **Hold-to-talk voice** - SR holds Right Option to trigger SaySo voice input (native HID event, press to start, release to stop)
- **Combo key support** - any button can fire a full key combination (e.g. B -> ⌘+Z for undo) without holding a modifier first
- **Analog stick mapping** - push the stick left/right to trigger arrow keys (handy for navigating AI code suggestions)
- **Auto-reconnect** - if Bluetooth drops, the script waits and reconnects automatically
- **Bluetooth watchdog** - optional `joycon_watchdog.py` daemon reconnects at the Bluetooth level via `blueutil` when HID is lost
- **JSON config** - all mappings live in `config.json`, human-editable and version-controllable
- **Web-based config UI** - optional browser interface for visual configuration (start `config_server.py` when you want it)

## Requirements

- macOS (tested on macOS 26 Tahoe, Apple Silicon)
- Joy-Con (R) paired via Bluetooth
- Python 3.9+
- Homebrew

## Installation

```bash
# 1. Install the native HID library
brew install hidapi

# 2. Install Python dependencies
pip3 install hidapi pynput

# 3. (optional) For the Bluetooth watchdog
brew install blueutil
```

> **Note:** Use `hidapi` (Cython binding), not `hid` (ctypes wrapper). If you have both installed, run `pip3 uninstall hid -y` to remove the conflicting one.

## Quick Start

```bash
cd joycon-vibe-keyboard
python3 joycon_mapper.py
```

The script reads `config.json`, prints the current mappings, and waits for a Joy-Con connection. Once connected, button presses are translated to keyboard events in real time.

Press `Ctrl+C` to stop.

## Configuration

All button mappings are stored in `config.json`:

```json
{
  "modifiers": {
    "R": ["cmd_r"],
    "ZR": ["cmd_r", "alt_r"],
    "SR": ["alt_r"]
  },
  "buttons": {
    "A": { "modifiers": [], "key": "enter" },
    "B": { "modifiers": ["cmd"], "key": "z" }
  },
  "stick": {
    "left": "up",
    "right": "down"
  }
}
```

There are three config sections:

- **modifiers** - buttons that act as hold-down modifier keys. The value is an array of key names (e.g. `["cmd_r"]` or `["cmd_r", "alt_r"]`). SR holds Right Option to trigger SaySo.
- **buttons** - action buttons that fire on press. Each has a `modifiers` array (empty for a single key, or filled for a combo like ⌘+Z) and a `key` for the main key.
- **stick** - maps stick push directions (`left`, `right`) to keyboard keys.

### Supported Key Names

| Category | Names |
|----------|-------|
| Special keys | `enter`, `tab`, `esc`, `backspace`, `delete`, `space`, `up`, `down`, `left`, `right` |
| Modifiers | `cmd`, `cmd_l`, `cmd_r`, `alt`, `alt_l`, `alt_r`, `ctrl`, `ctrl_l`, `ctrl_r`, `shift`, `shift_l`, `shift_r` |
| Function keys | `f1` through `f12` |
| Characters | `a`–`z`, `0`–`9` (single character as string) |

## Web Config UI (Optional)

If you prefer a visual interface for editing mappings:

```bash
python3 config_server.py
```

Then open `http://localhost:8766` in your browser. The page shows an SVG diagram of the Joy-Con with dropdown menus for each button. After making changes, click **Save** and restart `joycon_mapper.py` for the new mappings to take effect.

## Default Mappings

| Button | Keyboard | Vibe Coding Use |
|--------|----------|----------------|
| R (hold) | Right ⌘ | Trigger Typeless voice input |
| ZR (hold) | Right ⌘ + Right ⌥ | Secondary modifier combo |
| SR (hold) | Right ⌥ | Hold to trigger SaySo voice input |
| A | Enter | Confirm / send |
| B | ⌘+Z | Undo |
| X | Backspace | Delete |
| Y | Escape | Cancel / exit |
| PLUS | Tab | Accept AI code completion |
| MINUS | a | With R held -> ⌘+A select all |
| HOME | s | With R held -> ⌘+S save |
| STICK CLICK | d | With R held -> ⌘+D |
| SL | c | With R held -> ⌘+C copy |
| Stick left | ↑ | Navigate up in AI suggestions |
| Stick right | ↓ | Navigate down in AI suggestions |

> **Note on SR:** SR uses a native macOS HID event (Right Option, keycode 61) so SaySo recognizes the synthetic key. This requires Accessibility permission for the terminal running the mapper. SaySo does not accept the regular `pynput` synthetic event.

## Project Structure

```
joycon-vibe-keyboard/
├── joycon_mapper.py      # Main script - reads HID, simulates keyboard
├── config.json           # Button mapping configuration
├── config_server.py      # Optional web config server (port 8766)
├── joycon_watchdog.py    # Optional Bluetooth reconnect watchdog (blueutil)
├── web/
│   ├── joycon_config.html  # Interactive web config page
│   └── keymap.html         # Static reference page showing current mappings
├── tools/
│   ├── test_buttons.py     # Debug utility for button press detection
│   └── debug_stick.py      # Debug utility for analog stick values
├── assets/
│   ├── project-overview.png
│   └── vibe-coding-poster.png
├── docs/
│   └── DESIGN.md           # Architecture and design document (Chinese)
└── README.md             # This file
```

## How It Works

The script opens the Joy-Con as a Bluetooth HID device using `hidapi`, then polls for input reports (report ID `0x30` or `0x21`) at 4ms intervals. Button states are extracted from specific bit positions in the report payload. When a button transitions from released to pressed, the script simulates the corresponding keyboard event via `pynput`. The SR modifier uses a native Quartz `flagsChanged` event instead, so SaySo accepts it.

The analog stick's X-axis value is read from bytes 9–10 of the report. A deadzone of 600 around the center (~2048) prevents drift. On this particular hardware, the Y-axis is non-functional, so the X-axis is mapped to up/down instead.

If no data arrives for ~5 seconds, the script assumes the Joy-Con has disconnected and enters an auto-reconnect loop.

## Known Limitations

- **macOS only** - `pynput` and `hidapi` work on macOS; Linux/Windows would need minor adjustments
- **Accessibility permission required** - the terminal running the mapper needs macOS Accessibility permission for keyboard simulation; SR's native Right Option event also needs it
- **One process per HID device** - only one script can open the Joy-Con at a time; stop the mapper before running debug tools
- **No hot-reload** - changing `config.json` requires restarting `joycon_mapper.py`
- **Third-party Joy-Con quirks** - some aftermarket controllers have a dead Y-axis on the analog stick
- **Web config UI SR not synced** - the web config page still lists SR as a plain button; edit `config.json` directly for SR, or verify it after saving
- **Bluetooth range** - occasional drops at distance; auto-reconnect handles this gracefully

## License

Personal use project. No license.
