"""Joy-Con (R) HID button discovery tool."""
import hid
import sys

VENDOR_ID = 0x057e
PRODUCT_ID = 0x2006

def main():
    device = hid.device()
    try:
        device.open(VENDOR_ID, PRODUCT_ID)
    except Exception as e:
        print(f"Cannot open Joy-Con: {e}")
        print("Make sure Joy-Con is connected via Bluetooth.")
        sys.exit(1)

    print(f"Opened: {device.get_product_string()}")
    print("Press buttons on Joy-Con (R). Ctrl+C to quit.")
    print("-" * 60)

    device.set_nonblocking(True)

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
