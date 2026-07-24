"""
Joy-Con Mapper Configuration Server
====================================
Serves the config web page and handles saving mappings to config.json.
Also manages macOS LaunchAgent for auto-start on login.

Usage:
    python3 config_server.py
    then open http://localhost:8766
"""

import json
import os
import time
import subprocess
import shutil
from http.server import HTTPServer, SimpleHTTPRequestHandler

PORT = 8766
DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(DIR, "config.json")
HTML_FILE = os.path.join(DIR, "web", "joycon_config.html")
STATUS_FILE = os.path.join(DIR, "status.json")
PYTHON3 = shutil.which("python3") or "/usr/bin/env"
MAPPER_SCRIPT = os.path.join(DIR, "joycon_mapper.py")
PLIST_NAME = "com.joycon.mapper.plist"
PLIST_PATH = os.path.expanduser(f"~/Library/LaunchAgents/{PLIST_NAME}")

PLIST_CONTENT = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.joycon.mapper</string>
    <key>ProgramArguments</key>
    <array>
        <string>{PYTHON3}</string>
        <string>{MAPPER_SCRIPT}</string>
    </array>
    <key>WorkingDirectory</key>
    <string>{DIR}</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/joycon_mapper.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/joycon_mapper.err</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin</string>
    </dict>
</dict>
</plist>"""


class ConfigHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            with open(HTML_FILE, "rb") as f:
                self.wfile.write(f.read())
        elif self.path == "/api/config":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            with open(CONFIG_FILE, "r") as f:
                self.wfile.write(f.read().encode())
        elif self.path == "/api/autostart":
            enabled = os.path.exists(PLIST_PATH)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"enabled": enabled}).encode())
        elif self.path == "/api/status":
            state = "offline"
            ts = 0
            try:
                with open(STATUS_FILE, "r") as f:
                    d = json.load(f)
                    state = d.get("state", "offline")
                    ts = d.get("timestamp", 0)
                    # If connected but no heartbeat for 30s, treat as stale
                    if state == "connected" and (time.time() - ts) > 30:
                        state = "stale"
            except (FileNotFoundError, json.JSONDecodeError):
                pass
            # If mapper isn't running, check HID directly
            if state in ("offline", "stale"):
                try:
                    import hid as _hid
                    devices = _hid.enumerate(0x057e, 0x2007) + _hid.enumerate(0x057e, 0x2006)
                    if devices:
                        state = "connected"
                        ts = time.time()
                except Exception:
                    pass
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"state": state, "timestamp": ts}).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/api/config":
            content_length = int(self.headers["Content-Length"])
            body = self.rfile.read(content_length)
            try:
                config = json.loads(body)
                with open(CONFIG_FILE, "w") as f:
                    json.dump(config, f, indent=2, ensure_ascii=False)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"status": "ok"}')
                print("[OK] Config saved.")
            except Exception as e:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode())

        elif self.path == "/api/autostart/enable":
            try:
                os.makedirs(os.path.dirname(PLIST_PATH), exist_ok=True)
                with open(PLIST_PATH, "w") as f:
                    f.write(PLIST_CONTENT)
                subprocess.run(
                    ["launchctl", "load", "-w", PLIST_PATH],
                    capture_output=True, check=True,
                )
                self._json_ok("Auto-start enabled, mapper is running in the background")
                print("[OK] Auto-start enabled.")
            except Exception as e:
                self._json_err(str(e))

        elif self.path == "/api/autostart/disable":
            try:
                subprocess.run(
                    ["launchctl", "unload", "-w", PLIST_PATH],
                    capture_output=True,
                )
                if os.path.exists(PLIST_PATH):
                    os.remove(PLIST_PATH)
                self._json_ok("Auto-start disabled, mapper background process stopped")
                print("[OK] Auto-start disabled.")
            except Exception as e:
                self._json_err(str(e))

        else:
            self.send_response(404)
            self.end_headers()

    def _json_ok(self, msg):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"status": "ok", "message": msg}).encode())

    def _json_err(self, msg):
        self.send_response(500)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({"error": msg}).encode())

    def log_message(self, format, *args):
        pass  # Suppress default logging


def main():
    server = HTTPServer(("localhost", PORT), ConfigHandler)
    print(f"Joy-Con Mapper Config Server")
    print(f"Open in browser: http://localhost:{PORT}")
    print(f"Config file: {CONFIG_FILE}")
    print(f"Press Ctrl+C to stop.")
    print("-" * 40)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")
        server.server_close()


if __name__ == "__main__":
    main()
