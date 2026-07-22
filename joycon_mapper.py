"""
Joy-Con (R) → Keyboard Mapper for Vibe Coding
==============================================
Reads Joy-Con (R) button presses via Bluetooth HID and simulates keyboard shortcuts.
Lightweight, no Steam needed. Runs silently in background.
Auto-reconnects if Bluetooth disconnects.
Reads button mappings from config.json (edit via joycon_config.html).

Usage:
    python3 joycon_mapper.py

Requirements:
    brew install hidapi
    pip3 install hidapi pynput

Config:
    Edit config.json directly or run:
    python3 config_server.py
    then open http://localhost:8766
"""

import hid
import json
import os
import time
import sys
import atexit
from pynput.keyboard import Key, Controller, KeyCode

try:
    from Quartz import (
        CGEventCreateKeyboardEvent,
        CGEventPost,
        CGEventSetFlags,
        CGEventSetType,
        CGEventSourceCreate,
        kCGEventFlagMaskAlternate,
        kCGEventFlagsChanged,
        kCGEventSourceStateHIDSystemState,
        kCGHIDEventTap,
    )
    HAS_NATIVE_RIGHT_OPTION = True
except ImportError:
    HAS_NATIVE_RIGHT_OPTION = False

# ─── Config Loading ──────────────────────────────────────────────────────────

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
STATUS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "status.json")
RIGHT_OPTION_KEYCODE = 61


def write_status(state, extra=None):
    """Write connection status to status.json for the config server to read."""
    try:
        data = {"state": state, "timestamp": time.time()}
        if extra:
            data.update(extra)
        with open(STATUS_PATH, "w", encoding="utf-8") as f:
            json.dump(data, f)
    except Exception:
        pass


def set_modifier_state(keyboard, button_name, keys, is_pressed):
    """Press/release a modifier, using a native HID event for SaySo's SR key."""
    if button_name == "SR" and keys == [Key.alt_r] and HAS_NATIVE_RIGHT_OPTION:
        source = CGEventSourceCreate(kCGEventSourceStateHIDSystemState)
        event = CGEventCreateKeyboardEvent(source, RIGHT_OPTION_KEYCODE, is_pressed)
        CGEventSetType(event, kCGEventFlagsChanged)
        CGEventSetFlags(event, kCGEventFlagMaskAlternate if is_pressed else 0)
        CGEventPost(kCGHIDEventTap, event)
        return

    ordered_keys = keys if is_pressed else reversed(keys)
    for key in ordered_keys:
        if is_pressed:
            keyboard.press(key)
        else:
            keyboard.release(key)

# Map config string names → pynput Key objects
SPECIAL_KEYS = {
    "enter": Key.enter,
    "tab": Key.tab,
    "esc": Key.esc,
    "escape": Key.esc,
    "backspace": Key.backspace,
    "delete": Key.delete,
    "space": Key.space,
    "up": Key.up,
    "down": Key.down,
    "left": Key.left,
    "right": Key.right,
    "cmd": Key.cmd,
    "cmd_l": Key.cmd_l,
    "cmd_r": Key.cmd_r,
    "alt": Key.alt,
    "alt_l": Key.alt_l,
    "alt_r": Key.alt_r,
    "ctrl": Key.ctrl,
    "ctrl_l": Key.ctrl_l,
    "ctrl_r": Key.ctrl_r,
    "shift": Key.shift,
    "shift_l": Key.shift_l,
    "shift_r": Key.shift_r,
    "f1": Key.f1, "f2": Key.f2, "f3": Key.f3, "f4": Key.f4,
    "f5": Key.f5, "f6": Key.f6, "f7": Key.f7, "f8": Key.f8,
    "f9": Key.f9, "f10": Key.f10, "f11": Key.f11, "f12": Key.f12,
    "page_up": Key.page_up,
    "page_down": Key.page_down,
    "pageup": Key.page_up,
    "pagedown": Key.page_down,
    "home_key": Key.home,
    "end": Key.end,
}


def resolve_key(name):
    """Convert a config key name string to a pynput Key or KeyCode."""
    name = name.lower().strip()
    if name in SPECIAL_KEYS:
        return SPECIAL_KEYS[name]
    if len(name) == 1:
        return KeyCode.from_char(name)
    # Fallback: try as Key attribute
    if hasattr(Key, name):
        return getattr(Key, name)
    raise ValueError(f"Unknown key name in config: '{name}'")


def load_config():
    """Load config.json and return (modifiers, buttons, stick) dicts with pynput keys."""
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    # Modifiers: {"R": [Key.cmd_r], "ZR": [Key.cmd_r, Key.alt_r]}
    modifiers = {}
    for btn, key_names in cfg.get("modifiers", {}).items():
        modifiers[btn] = [resolve_key(k) for k in key_names]

    # Buttons: split into plain buttons and combos based on "modifiers" field
    buttons = {}
    combos = {}
    for btn, mapping in cfg.get("buttons", {}).items():
        key = resolve_key(mapping["key"])
        mods = [resolve_key(m) for m in mapping.get("modifiers", [])]
        if mods:
            combos[btn] = (mods, key)
        else:
            buttons[btn] = key

    # Stick: {"left": Key.up, "right": Key.down}
    stick_cfg = cfg.get("stick", {})
    stick = {}
    for direction, key_name in stick_cfg.items():
        stick[direction] = resolve_key(key_name)

    return modifiers, buttons, combos, stick


# ─── Joy-Con HID Constants ───────────────────────────────────────────────────
VENDOR_ID = 0x057e
PRODUCT_ID = 0x2006

STICK_DEADZONE = 600
STICK_CENTER = 2048

# Button bit positions in the 0x30 input report
BUTTON_BITS = {
    # Byte 3: Right Joy-Con buttons
    "Y":     (3, 0x01),
    "X":     (3, 0x02),
    "B":     (3, 0x04),
    "A":     (3, 0x08),
    "SR":    (3, 0x10),
    "SL":    (3, 0x20),
    "R":     (3, 0x40),
    "ZR":    (3, 0x80),
    # Byte 4: Shared buttons
    "MINUS":       (4, 0x01),
    "PLUS":        (4, 0x02),
    "STICK_CLICK": (4, 0x04),
    "HOME":        (4, 0x10),
}


def key_display_name(k):
    """Get a display name for a pynput key."""
    if hasattr(k, "name"):
        return k.name
    if hasattr(k, "char") and k.char:
        return k.char
    return str(k)


def connect_joycon():
    """Try to connect to Joy-Con, return device or None."""
    device = hid.device()
    try:
        device.open(VENDOR_ID, PRODUCT_ID)
        return device
    except Exception:
        return None


def release_all_keys(keyboard, modifiers, stick, stick_state):
    """Release any held modifier and stick keys."""
    for button_name, keys in modifiers.items():
        try:
            set_modifier_state(keyboard, button_name, keys, False)
        except Exception:
            pass
    for direction, key in stick.items():
        if stick_state.get(direction):
            try:
                keyboard.release(key)
            except Exception:
                pass


def main():
    # Load config
    try:
        MODIFIERS, BUTTONS, COMBOS, STICK = load_config()
    except FileNotFoundError:
        print(f"[ERROR] Config file not found: {CONFIG_PATH}")
        print("Create config.json or run config_server.py to generate one.")
        sys.exit(1)
    except (json.JSONDecodeError, ValueError) as e:
        print(f"[ERROR] Failed to parse config: {e}")
        sys.exit(1)

    keyboard = Controller()

    print("Joy-Con (R) → Keyboard Mapper for Vibe Coding")
    print("=" * 50)
    print(f"Config: {CONFIG_PATH}")
    print()
    if MODIFIERS:
        print("Modifier buttons (hold):")
        for btn, keys in MODIFIERS.items():
            names = "+".join(key_display_name(k) for k in keys)
            print(f"  {btn:12s} → hold {names}")
        print()
    if BUTTONS:
        print("Action buttons (press):")
        for btn, key in BUTTONS.items():
            print(f"  {btn:12s} → {key_display_name(key)}")
        print()
    if COMBOS:
        print("Combo buttons (direct shortcuts):")
        for btn, (mods, key) in COMBOS.items():
            mod_str = "+".join(key_display_name(m) for m in mods)
            print(f"  {btn:12s} → {mod_str}+{key_display_name(key)}")
        print()
    if STICK:
        print("Stick mappings:")
        for direction, key in STICK.items():
            print(f"  push {direction.upper():8s} → {key_display_name(key)}")
        print()
    print("Tip: Hold a modifier + press any action button = modifier + that key")
    print()

    # ── Auto-reconnect loop ──
    atexit.register(lambda: write_status("stopped"))

    try:
        while True:
            print("[...] Waiting for Joy-Con (R)...")
            write_status("waiting")
            device = None
            while device is None:
                device = connect_joycon()
                if device is None:
                    time.sleep(2)

            print(f"[OK] Connected: {device.get_product_string()}")
            print("Running... Press Ctrl+C to stop.")
            print("-" * 50)
            write_status("connected")
            last_heartbeat = time.time()

            device.set_nonblocking(True)
            prev_buttons = {name: False for name in BUTTON_BITS}
            stick_state = {d: False for d in STICK}
            no_data_count = 0

            try:
                while True:
                    data = device.read(64)
                    if not data:
                        no_data_count += 1
                        if no_data_count > 1250:  # ~5s no data = disconnected
                            print("\n[!] Joy-Con disconnected.")
                            break
                        time.sleep(0.004)
                        continue

                    no_data_count = 0

                    # Heartbeat: update timestamp every 5s (cheap write)
                    now = time.time()
                    if now - last_heartbeat > 5:
                        write_status("connected")
                        last_heartbeat = now
                    report_id = data[0]
                    if report_id not in (0x30, 0x21):
                        continue
                    if len(data) < 11:
                        continue

                    # ── Process buttons ──
                    for name, (byte_idx, bit_mask) in BUTTON_BITS.items():
                        is_pressed = bool(data[byte_idx] & bit_mask)
                        was_pressed = prev_buttons[name]

                        if is_pressed and not was_pressed:
                            if name in MODIFIERS:
                                set_modifier_state(keyboard, name, MODIFIERS[name], True)
                                names = "+".join(key_display_name(k) for k in MODIFIERS[name])
                                print(f"  [{name}] ↓ hold {names}")
                            elif name in COMBOS:
                                mods, key = COMBOS[name]
                                for m in mods:
                                    keyboard.press(m)
                                keyboard.press(key)
                                keyboard.release(key)
                                for m in reversed(mods):
                                    keyboard.release(m)
                                mod_str = "+".join(key_display_name(m) for m in mods)
                                print(f"  [{name}] → {mod_str}+{key_display_name(key)}")
                            elif name in BUTTONS:
                                keyboard.press(BUTTONS[name])
                                keyboard.release(BUTTONS[name])
                                print(f"  [{name}] → {key_display_name(BUTTONS[name])}")

                        elif not is_pressed and was_pressed:
                            if name in MODIFIERS:
                                set_modifier_state(keyboard, name, MODIFIERS[name], False)
                                names = "+".join(key_display_name(k) for k in MODIFIERS[name])
                                print(f"  [{name}] ↑ release {names}")

                        prev_buttons[name] = is_pressed

                    # ── Analog stick ──
                    # X axis: ((data[10] & 0x0F) << 8) | data[9]
                    # Only X axis works on this hardware (Y axis dead)
                    if STICK:
                        stick_x = ((data[10] & 0x0F) << 8) | data[9]

                        # "left" direction = stick pushed left (value < center)
                        # "right" direction = stick pushed right (value > center)
                        want_left = stick_x < STICK_CENTER - STICK_DEADZONE
                        want_right = stick_x > STICK_CENTER + STICK_DEADZONE

                        if "left" in STICK:
                            key = STICK["left"]
                            if want_left and not stick_state.get("left"):
                                keyboard.press(key)
                                print(f"  [STICK] ← → {key_display_name(key)}")
                            elif not want_left and stick_state.get("left"):
                                keyboard.release(key)
                            stick_state["left"] = want_left

                        if "right" in STICK:
                            key = STICK["right"]
                            if want_right and not stick_state.get("right"):
                                keyboard.press(key)
                                print(f"  [STICK] → → {key_display_name(key)}")
                            elif not want_right and stick_state.get("right"):
                                keyboard.release(key)
                            stick_state["right"] = want_right

            except OSError:
                print("\n[!] Joy-Con connection lost.")
                write_status("disconnected")
            finally:
                release_all_keys(keyboard, MODIFIERS, STICK, stick_state)
                try:
                    device.close()
                except Exception:
                    pass

    except KeyboardInterrupt:
        print("\n[STOP] Mapper stopped.")
        write_status("stopped")


if __name__ == "__main__":
    main()
