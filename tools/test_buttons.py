"""Joy-Con (R) HID button discovery tool."""
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
        print("Cannot open Joy-Con (tried both PIDs).")
        print("Make sure Joy-Con is connected via Bluetooth.")
        sys.exit(1)

    print(f"Opened: {device.get_product_string()}")
    print("Press buttons on Joy-Con (R). Ctrl+C to quit.")
    print("-" * 60)

    device.set_nonblocking(True)
    # 原厂 Joy-Con 默认发 0x3f,激活到 0x30 标准模式
    device.write(bytes([0x01, 0x00, 0, 0, 0, 0, 0, 0, 0, 0, 0x03, 0x30]))
    time.sleep(0.1)

    try:
        while True:
            data = device.read(64)
            if data:
                # Print report ID and first 12 bytes in hex
                report_id = data[0]
                hex_str = " ".join(f"{b:02x}" for b in data[:12])
                print(f"Report 0x{report_id:02x}: {hex_str}")
    except KeyboardInterrupt:
        print("\nBye!")
    finally:
        device.close()

if __name__ == "__main__":
    main()
