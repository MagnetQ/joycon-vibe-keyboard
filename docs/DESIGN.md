# Joy-Con Vibe Coding — Mapping Configuration Tool Design Document

## Project Overview

Use a Joy-Con (R) controller as a shortcut keyboard for Vibe Coding. Read controller buttons via Bluetooth HID and map them to keyboard shortcuts. This tool provides a browser-based visual interface for users to freely configure button mappings, supporting single keys, combo keys, and stick direction mapping.

## System Architecture

```
┌─────────────────┐  read/write  ┌──────────────┐
│  Browser Config  │ ─────────── │  config.json  │
│  Page            │   HTTP API  │              │
│ joycon_config    │             └──────┬───────┘
│   .html          │                    │ read on startup
└────────┬─────────┘                    ▼
         │                              ┌──────────────────┐
         │ hosts page                   │  joycon_mapper.py │
         ▼                              │  (Bluetooth HID   │
┌─────────────────┐                     │   read            │
│ config_server.py │                     │   + keyboard      │
│ (local HTTP      │                     │     emulation)   │
│  server)         │                     └──────────────────┘
└─────────────────┘
```

**Four file responsibilities**:

| File | Role | Description |
|------|------|-------------|
| `config.json` | Config source | Single source of truth, JSON format, stores all button mappings |
| `config_server.py` | Server | Python HTTP server (port 8766), provides API + hosts HTML |
| `joycon_config.html` | Frontend UI | Interactive configuration page, SVG controller diagram + dropdown menus |
| `joycon_mapper.py` | Runtime | Loads mappings from config.json on startup, reads buttons via Bluetooth HID and emulates keyboard |

## config.json Format Specification

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

**Three configuration sections**:

- `modifiers` — Modifier keys (active while held). Key is the controller button name (R / ZR / SR), value is an array of keyboard modifier key names. While R is held, all normal key presses automatically have this modifier applied.
- `buttons` — Action buttons (triggered on press). Each button contains two fields: `modifiers` (optional combo key prefix, empty array means none) and `key` (primary key). The mapper automatically distinguishes between "normal keys" and "combo keys" based on whether modifiers is empty.
- `stick` — Stick direction mapping. Key is the physical direction (left / right), value is the keyboard arrow key.

**Key Name Convention**:

- Special keys: `enter`, `tab`, `esc`, `backspace`, `delete`, `space`, `up`, `down`, `left`, `right`
- Modifier keys: `cmd`, `cmd_l`, `cmd_r`, `alt`, `alt_l`, `alt_r`, `ctrl`, `ctrl_l`, `ctrl_r`, `shift`, `shift_l`, `shift_r`
- Function keys: `f1` ~ `f12`
- Letters/digits: use the character directly, e.g. `"a"`, `"z"`, `"1"`

## config_server.py Design

**Technology choice**: Python built-in `http.server`, zero external dependencies.

**Port**: 8766

**API endpoints**:

| Method | Path | Description |
|--------|------|-------------|
| `GET /` | `/` | Return the joycon_config.html page |
| `GET /api/config` | `/api/config` | Return current config.json contents (JSON) |
| `POST /api/config` | `/api/config` | Receive JSON body, write to config.json |
| `GET /api/autostart` | `/api/autostart` | Return auto-start status `{"enabled": bool}` |
| `GET /api/status` | `/api/status` | Return controller connection status (reads status.json, fallback uses hid.enumerate for direct detection) |
| `POST /api/autostart/enable` | `/api/autostart/enable` | Create LaunchAgent plist + launchctl load |
| `POST /api/autostart/disable` | `/api/autostart/disable` | launchctl unload + delete plist |

**Startup command**:

```bash
cd joycon-vibe-keyboard
python3 config_server.py
# Open browser to http://localhost:8766
```

## joycon_config.html Page Design

### Overall Layout

```
┌──────────────────────────────────────────────────────────┐
│  Joy-Con (R) Button Mapping Configuration        [Save]  │
├───────────────────────┬──────────────────────────────────┤
│                       │                                  │
│    ┌─────────┐        │  ── Modifier Keys (hold) ──      │
│    │         │        │  R  hold triggers: [Right Cmd ▾]  │
│    │  SVG    │        │  ZR hold triggers: [R Cmd+R Opt ▾]│
│    │  Joy-Con│        │                                  │
│    │  (R)    │        │  ── Action Buttons (press) ──     │
│    │  diagram│        │  A  [None ▾]  +  [Enter ▾]       │
│    │         │        │  B  [⌘ ▾]    +  [z ▾]            │
│    │  labels │        │  X  [None ▾]  +  [Backspace ▾]   │
│    │  show   │        │  Y  [None ▾]  +  [Escape ▾]      │
│    │  each   │        │  ...                             │
│    │  button │        │                                  │
│    │  position│       │  ── Stick Direction ──            │
│    │         │        │  Push Left: [↑ ▾] Push Right: [↓ ▾]│
│    └─────────┘        │                                  │
└───────────────────────┴──────────────────────────────────┘
```

### Visual Style

- Dark theme (`#1a1a2e` background, `#e0e0e0` text), consistent with keymap.html
- Left side SVG diagram: Joy-Con (R) outline with button positions labeled, highlights on hover
- Right side configuration area: grouped into "Modifier Keys", "Action Buttons", "Stick" sections
- Each action button gets one row with two dropdowns side by side: modifier dropdown + primary key dropdown
- Save button in the top-right corner, clicking shows a toast at the bottom: "Saved successfully" or "Save failed"

### Dropdown Options

**Modifier dropdown** (left side of action buttons):

| Display | Value |
|---------|-------|
| None | `[]` |
| ⌘ | `["cmd"]` |
| ⌘+⇧ | `["cmd", "shift"]` |
| ⌘+⌥ | `["cmd", "alt"]` |
| ⇧ | `["shift"]` |
| ⌥ | `["alt"]` |
| ⌃ | `["ctrl"]` |
| ⌘+⌃ | `["cmd", "ctrl"]` |

**Primary key dropdown** (right side of action buttons):

Enter, Tab, Escape, Backspace, Delete, Space, ↑ ↓ ← →, A–Z, 0–9, F1–F12

**Modifier hold trigger dropdown** (R / ZR specific):

Right Command, Right Command + Right Option, Right Option, Right Shift, None

**Stick direction dropdown**:

↑, ↓, ←, →, None

### Interaction Behavior

- On page load, `GET /api/config` fetches current configuration and populates all dropdowns
- After the user modifies any dropdown, clicking the "Save" button sends `POST /api/config` with the entire configuration
- Save success: green toast at bottom "Saved successfully, restart mapper to apply"
- Save failure: red toast at bottom "Save failed: {error message}"
- No auto-save on change, to avoid writing incomplete configurations while the user is mid-edit

## joycon_mapper.py Refactoring

**Refactoring goal**: Remove all hardcoded MODIFIERS / BUTTONS / COMBOS dictionaries, replace with loading from config.json on startup.

**New `load_config()` function**:

1. Read config.json
2. Convert string key names to pynput `Key` or `KeyCode` objects
3. For each button in `buttons`, check if `modifiers` is empty to automatically split into "normal keys" and "combo keys"
4. Return `(modifiers, buttons, combos, stick)` — four dictionaries

**Key name resolution rules**:

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

**Startup logging**: Print all currently loaded mappings so the user can confirm the configuration is active.

**Everything else unchanged**: Bluetooth HID reading logic, auto-reconnect, stick handling remain as-is.

## Usage Workflow

```
First time use:
  1. Terminal: python3 config_server.py
  2. Browser: http://localhost:8766
  3. Configure button mappings on the page, click Save
  4. Terminal: python3 joycon_mapper.py
  5. Start using the Joy-Con

Modifying configuration:
  1. Stop joycon_mapper.py (Ctrl+C)
  2. Open the configuration page in browser, change mappings, save
  3. Restart joycon_mapper.py

Daily startup:
  1. python3 joycon_mapper.py (reads the previous config.json directly)
```

## Current Default Mapping

| Controller Button | Keyboard Mapping | Vibe Coding Purpose |
|-------------------|------------------|---------------------|
| R (hold) | Right Command | Trigger Typeless voice input |
| ZR (hold) | Right Cmd + Right Opt | Backup combo modifier |
| A | Enter | Confirm / Send |
| B | ⌘+Z | Undo |
| X | Backspace | Delete |
| Y | Escape | Cancel / Exit |
| PLUS | Tab | Accept AI autocomplete suggestion |
| MINUS | a | Combined with R key = ⌘+A Select All |
| HOME | Hold ⌘, each press triggers one Tab | Select one by one at your own pace; stops and confirms 0.8s after last press |
| STICK_CLICK | d | Combined with R key = ⌘+D |
| SL | c | Combined with R key = ⌘+C Copy |
| SR (hold) | Right Option (alt_r) | Hold to wake SaySo voice input |
| Stick Left | ↑ | Move up (select code suggestions) |
| Stick Right | ↓ | Move down (select code suggestions) |

## Known Limitations

- Joy-Con Y-axis is physically broken (third-party controller), stick only works on X-axis; left/right mapped to up/down directions
- On macOS, only one process can open an HID device at a time; while the mapper is running, other debug scripts cannot connect
- Configuration changes require restarting the mapper to take effect (no hot-reload)
- Bluetooth connection is considered disconnected after ~5 seconds of no data, auto-reconnect is triggered
