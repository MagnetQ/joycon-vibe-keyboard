"""Joy-Con (R) 摇杆实时监视工具。

显示摇杆 X/Y 轴原始值(12-bit,0-4095,中心约 2048),
用来确认摇杆数据能否读到、各方向数值范围。

Usage:
    先停掉 joycon_mapper.py(它会占用设备),然后:
    python3 tools/stick_monitor.py
    推摇杆 上/下/左/右,看 X/Y 数值变化。Ctrl+C 退出。
"""
import hid
import sys
import time

VENDOR_ID = 0x057e
PRODUCT_IDS = (0x2007, 0x2006)


def main():
    device = None
    for pid in PRODUCT_IDS:
        device = hid.device()
        try:
            device.open(VENDOR_ID, pid)
            break
        except Exception:
            device = None
    if device is None:
        print("打不开 Joy-Con(试了两个 PID)。确认 mapper 已停 + 手柄蓝牙连着。")
        sys.exit(1)

    print(f"Opened: {device.get_product_string()}")
    device.set_nonblocking(True)
    # 原厂 Joy-Con 默认发 0x3f,激活到 0x30 标准模式
    device.write(bytes([0x01, 0x00, 0, 0, 0, 0, 0, 0, 0, 0, 0x03, 0x30]))
    time.sleep(0.15)

    print("推摇杆 上/下/左/右,看 X/Y 变化。Ctrl+C 退出。")
    print("-" * 50)
    prev = None
    try:
        while True:
            data = device.read(64)
            if not data or data[0] != 0x30 or len(data) < 12:
                time.sleep(0.01)
                continue
            # 右摇杆标准解析(Joy-Con R 摇杆数据在 byte 9-11)
            x = data[9] | ((data[10] & 0x0F) << 8)
            y = ((data[10] & 0xF0) >> 4) | (data[11] << 4)
            if (x, y) != prev:
                dx = x - 2048
                dy = y - 2048
                print(f"X={x:4d} (Δ{dx:+5d})  Y={y:4d} (Δ{dy:+5d})")
                prev = (x, y)
    except KeyboardInterrupt:
        print("\n退出")
    finally:
        device.close()


if __name__ == "__main__":
    main()
