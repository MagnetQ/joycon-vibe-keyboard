"""
Joy-Con Bluetooth Auto-Reconnect Watchdog
==========================================
Monitors Joy-Con (R) Bluetooth connection and auto-reconnects when it drops.
Runs as a background daemon (via LaunchAgent or manually).

Checks every 10 seconds:
  1. Is Joy-Con visible via HID? (hid.enumerate)
  2. If not visible, try blueutil to reconnect at Bluetooth level
  3. Log all events to /tmp/joycon_watchdog.log

Usage:
    python3 joycon_watchdog.py          # run in foreground
    python3 joycon_watchdog.py --daemon  # run in background

Requirements:
    brew install blueutil
    pip3 install hidapi
"""

import hid
import time
import subprocess
import os
import sys
import signal
import json
import shutil

VENDOR_ID = 0x057e
PRODUCT_IDS = (0x2007, 0x2006)
CHECK_INTERVAL = 30      # seconds between checks when connected
RECONNECT_INTERVAL = 10  # seconds between reconnect attempts when disconnected
BLUEUTIL_PATH = shutil.which("blueutil") or "/opt/homebrew/bin/blueutil"

LOG_FILE = "/tmp/joycon_watchdog.log"
STATUS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "status.json")

# Track state
last_state = None
joycon_address = None


def log(msg):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    try:
        with open(LOG_FILE, "a") as f:
            f.write(line + "\n")
    except Exception:
        pass


def write_status(state):
    """Write status for config_server to read."""
    try:
        with open(STATUS_PATH, "w") as f:
            json.dump({"state": state, "timestamp": time.time()}, f)
    except Exception:
        pass


def find_joycon_address():
    """Find Joy-Con MAC address from system_profiler."""
    global joycon_address
    if joycon_address:
        return joycon_address
    try:
        out = subprocess.check_output(
            ["system_profiler", "SPBluetoothDataType", "-json"],
            timeout=5
        ).decode()
        data = json.loads(out)
        bt = data.get("SPBluetoothDataType", [{}])[0]
        for key in bt:
            if "device" in key:
                items = bt[key]
                if isinstance(items, list):
                    for item in items:
                        if isinstance(item, dict):
                            for name, info in item.items():
                                if "joy-con" in name.lower() and isinstance(info, dict):
                                    addr = info.get("device_address", "")
                                    if addr:
                                        joycon_address = addr
                                        return addr
    except Exception as e:
        log(f"WARN: Failed to find Joy-Con address: {e}")
    return None


def is_joycon_hid_present():
    """Check if Joy-Con is visible via HID enumerate."""
    try:
        return any(hid.enumerate(VENDOR_ID, pid) for pid in PRODUCT_IDS)
    except Exception:
        return False


def blueutil_available():
    """Check if blueutil is installed."""
    return os.path.exists(BLUEUTIL_PATH)


def blueutil_reconnect():
    """Try to reconnect Joy-Con via blueutil."""
    addr = find_joycon_address()
    if not addr:
        log("WARN: No Joy-Con MAC address found. Pair the device first.")
        return False
    if not blueutil_available():
        log("WARN: blueutil not installed. Run: brew install blueutil")
        return False

    log(f"Attempting Bluetooth reconnect to {addr}...")
    try:
        # First disconnect if in weird state
        subprocess.run(
            [BLUEUTIL_PATH, "--disconnect", addr],
            capture_output=True, timeout=5
        )
        time.sleep(1)
        # Then connect
        result = subprocess.run(
            [BLUEUTIL_PATH, "--connect", addr],
            capture_output=True, timeout=15, text=True
        )
        if result.returncode == 0:
            log(f"Bluetooth connect command succeeded.")
            return True
        else:
            log(f"Bluetooth connect failed: {result.stderr.strip()}")
            return False
    except subprocess.TimeoutExpired:
        log("WARN: blueutil connect timed out.")
        return False
    except Exception as e:
        log(f"WARN: blueutil error: {e}")
        return False


def main():
    global last_state

    daemon = "--daemon" in sys.argv
    if daemon:
        # Fork to background
        if os.fork() > 0:
            print(f"Watchdog started in background. Log: {LOG_FILE}")
            sys.exit(0)
        # Redirect stdout/stderr
        sys.stdout = open("/dev/null", "w")
        sys.stderr = open("/dev/null", "w")

    # Handle graceful shutdown
    running = True
    def shutdown(signum, frame):
        nonlocal running
        running = False
    signal.signal(signal.SIGTERM, shutdown)
    signal.signal(signal.SIGINT, shutdown)

    log("Joy-Con Watchdog started.")
    log(f"  Vendor: 0x{VENDOR_ID:04x}, Products: {[hex(p) for p in PRODUCT_IDS]}")
    log(f"  Check interval: {CHECK_INTERVAL}s (connected), {RECONNECT_INTERVAL}s (reconnecting)")
    log(f"  blueutil: {'available' if blueutil_available() else 'NOT installed'}")
    addr = find_joycon_address()
    if addr:
        log(f"  Joy-Con MAC: {addr}")
    else:
        log("  Joy-Con MAC: not found (will retry)")

    while running:
        present = is_joycon_hid_present()

        if present:
            if last_state != "connected":
                log("Joy-Con connected (HID present).")
                write_status("connected")
            last_state = "connected"
        else:
            if last_state != "disconnected":
                log("Joy-Con disconnected (HID gone).")
                write_status("disconnected")
                # Try Bluetooth reconnect
                blueutil_reconnect()
            else:
                # Still disconnected, retry reconnect periodically
                if time.time() % 60 < CHECK_INTERVAL:  # retry every ~60s
                    blueutil_reconnect()
            last_state = "disconnected"

        # Sleep in small chunks so we can respond to signals
        interval = RECONNECT_INTERVAL if last_state == "disconnected" else CHECK_INTERVAL
        for _ in range(interval):
            if not running:
                break
            time.sleep(1)

    log("Watchdog stopped.")
    write_status("stopped")


if __name__ == "__main__":
    main()
