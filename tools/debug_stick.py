"""Joy-Con (R) stick byte debugger.

Prints only bytes that CHANGE between frames, so you can see which byte
moves when you push the stick in each direction.

Usage:
    python3 debug_stick.py

Then push stick UP / DOWN / LEFT / RIGHT and watch which [N] bytes change.
"""
import hid
import sys
import time

VENDOR_ID = 0x057e
PRODUCT_ID = 0x2006


def main():
    device = hid.device()
    try:
        device.open(VENDOR_ID, PRODUCT_ID)
    except Exception as e:
        print(f"Cannot open Joy-Con: {e}")
        print("Make sure it's connected via Bluetooth.")
        sys.exit(1)

    print(f"Opened: {device.get_product_string()}")
    print()
    print("Push stick UP / DOWN / LEFT / RIGHT.")
    print("Watch which [N] bytes change for each direction.")
    print("Tip: push UP and remember which bytes move, then DOWN, LEFT, RIGHT.")
    print("Ctrl+C to quit.")
    print("-" * 60)

    device.set_nonblocking(True)
    prev = None

    try:
        while True:
            data = device.read(64)
            if not data:
                time.sleep(0.004)
                continue

            report_id = data[0]
            if report_id not in (0x30, 0x21):
                continue
            if len(data) < 16:
                continue

            if prev is None:
                prev = bytes(data[:16])
                print(f"report 0x{report_id:02x} init:")
                print("  " + " ".join(f"[{i}]={b:3d}" for i, b in enumerate(data[:16])))
                print("-" * 60)
                continue

            changes = []
            for i in range(16):
                if data[i] != prev[i]:
                    changes.append(f"[{i}] {prev[i]:3d}->{data[i]:3d}")
            if changes:
                print(f"r{report_id:02x} " + " ".join(changes))

            prev = bytes(data[:16])
    except KeyboardInterrupt:
        print("\nBye!")
    finally:
        device.close()


if __name__ == "__main__":
    main()
