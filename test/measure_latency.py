#!/usr/bin/env python3
"""Measure iKeys HID latency for keyboard, mouse, and media keys.

Measures two latency components:
  - Firmware processing: WS receive -> HID send (from [TIMING] serial output)
  - End-to-end via evdev: WS send -> HID press on host (polling active_keys)

Uses EVIOCGKEY (active_keys) instead of the event stream to avoid
OS auto-repeat and stale event buffer issues.

Usage:
  # Keyboard key 'a'
  python3 test/measure_latency.py --host 192.168.1.x --type key --key a

  # Mouse left button
  python3 test/measure_latency.py --host 192.168.1.x --type mouse

  # Media play key
  python3 test/measure_latency.py --host 192.168.1.x --type media

  # All with custom samples
  python3 test/measure_latency.py --host 192.168.1.x --type key --samples 100 --key w

Requirements: pyserial, websocket-client, evdev (for HID arrival timing)
"""

import argparse
import os
import queue
import re
import sys
import threading
import time

# Prevent proxy interference with WebSocket connections
for _k in ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY', 'NO_PROXY']:
    os.environ.pop(_k, None)

try:
    import serial
except ImportError:
    print("ERROR: pyserial not installed. Run: pip install pyserial")
    sys.exit(1)

try:
    from websocket import create_connection
except ImportError:
    print("ERROR: websocket-client not installed. Run: pip install websocket-client")
    sys.exit(1)

TIMING_RE = re.compile(rb'\[TIMING\] ([KMC]) ws=(\d+) hid=(\d+) fw_us=(\d+)')

# Printable ASCII characters -> Linux input event codes
CHAR_TO_LINUX = {
    'a': 30, 'b': 48, 'c': 46, 'd': 32, 'e': 18, 'f': 33,
    'g': 34, 'h': 35, 'i': 23, 'j': 36, 'k': 37, 'l': 38,
    'm': 50, 'n': 49, 'o': 24, 'p': 25, 'q': 16, 'r': 19,
    's': 31, 't': 20, 'u': 22, 'v': 47, 'w': 17, 'x': 45,
    'y': 21, 'z': 44,
    'A': 30, 'B': 48, 'C': 46, 'D': 32, 'E': 18, 'F': 33,
    'G': 34, 'H': 35, 'I': 23, 'J': 36, 'K': 37, 'L': 38,
    'M': 50, 'N': 49, 'O': 24, 'P': 25, 'Q': 16, 'R': 19,
    'S': 31, 'T': 20, 'U': 22, 'V': 47, 'W': 17, 'X': 45,
    'Y': 21, 'Z': 44,
    '0': 11, '1': 2, '2': 3, '3': 4, '4': 5,
    '5': 6, '6': 7, '7': 8, '8': 9, '9': 10,
    ' ': 57, '-': 12, '=': 13, '[': 26, ']': 27, '\\': 43,
    ';': 39, "'": 40, '`': 41, ',': 51, '.': 52, '/': 53,
}

# HID type -> expected Linux evdev code for press detection
# Mouse left button = BTN_LEFT (272), MEDIA play/pause = KEY_PLAYPAUSE (164)
HID_TYPE_EVCODE = {
    'mouse': 272,    # BTN_LEFT
    'media': 164,    # KEY_PLAYPAUSE
}


def serial_reader(ser, q, stop):
    """Background thread: read Serial lines, queue parsed timing data."""
    while not stop.is_set():
        try:
            line = ser.readline()
        except serial.SerialException:
            break
        if not line:
            continue
        m = TIMING_RE.search(line)
        if m:
            q.put({
                't_host': time.monotonic_ns(),
                'fw_us': int(m.group(4)),
                'type': m.group(1).decode(),
            })


def find_evdev_device(dev_type):
    """Find ESP32 HID evdev device by type: 'keyboard', 'mouse', or 'consumer'.

    Returns (device, ecodes_module) or (None, None).
    The device is matched by 'ESP32' in the name and interface-specific capabilities.
    """
    try:
        import evdev
        from evdev import ecodes
    except ImportError:
        return None, None

    checks = {
        'keyboard': lambda caps, e: e.EV_KEY in caps and e.KEY_A in caps.get(e.EV_KEY, []),
        'mouse': lambda caps, e: e.EV_KEY in caps and e.BTN_MOUSE in caps.get(e.EV_KEY, []),
        'consumer': lambda caps, e: e.EV_KEY in caps and e.KEY_PLAY in caps.get(e.EV_KEY, []),
    }
    check = checks.get(dev_type, checks['keyboard'])

    for path in evdev.list_devices():
        try:
            dev = evdev.InputDevice(path)
            if 'ESP32' not in dev.name:
                dev.close()
                continue
            caps = dev.capabilities()
            if check(caps, ecodes):
                return dev, ecodes
            dev.close()
        except (OSError, PermissionError):
            continue
    return None, None


def wait_for_hid_key(dev, expected_linux_code, timeout_s=1.0):
    """Poll active_keys() until the expected Linux keycode is pressed.

    Returns host monotonic ns when the key first appears, or None on timeout.
    Uses EVIOCGKEY (active_keys) — no event buffer, no auto-repeat issues.
    """
    if dev is None:
        return None
    start = time.monotonic()
    while time.monotonic() - start < timeout_s:
        try:
            keys = dev.active_keys()
        except (OSError, RuntimeError):
            return None
        if expected_linux_code in keys:
            return time.monotonic_ns()
        time.sleep(0.0005)
    return None


def wait_for_hid_event(dev, expected_linux_code, timeout_s=1.0):
    """Read from the event stream until the expected key is pressed.

    Used for consumer/media keys which are not reported by active_keys().
    Detects a press event (type=EV_KEY=1, value=1).
    Returns host monotonic ns when the key first appears, or None on timeout.
    """
    if dev is None:
        return None
    start = time.monotonic()
    while time.monotonic() - start < timeout_s:
        try:
            ev = dev.read_one()
        except (OSError, RuntimeError):
            return None
        if ev is not None and ev.type == 1 and ev.code == expected_linux_code and ev.value == 1:
            return time.monotonic_ns()
        time.sleep(0.0005)
    return None


def to_release(key):
    """Convert a press message to its release form (prepend ~)."""
    return '~' + key


def main():
    p = argparse.ArgumentParser(description='Measure iKeys HID latency')
    p.add_argument('--host', required=True, help='ESP32 hostname or IP address')
    p.add_argument('--serial', default='/dev/ttyUSB0',
                   help='Serial port (default: /dev/ttyUSB0)')
    p.add_argument('--baud', type=int, default=115200,
                   help='Serial baud rate (default: 115200)')
    p.add_argument('--samples', type=int, default=30,
                   help='Number of measurement samples (default: 30)')
    p.add_argument('--type', default='key', choices=['key', 'mouse', 'media'],
                   help='HID action type: key (single char), mouse (left click), or media (play)')
    p.add_argument('--key', default='w',
                   help='Key string to send (default: w). For mouse type this is ignored (uses *Cn). For media type this is ignored (uses *MEDplay).')
    p.add_argument('--interval', type=float, default=0.3,
                   help='Delay between presses in seconds (default: 0.3)')
    args = p.parse_args()

    # Determine press string and expected evdev code
    if args.type == 'mouse':
        press_key = '*Cn'
        expected_linux = HID_TYPE_EVCODE['mouse']
        evdev_type = 'mouse'
    elif args.type == 'media':
        press_key = '*MEDplay'
        expected_linux = HID_TYPE_EVCODE['media']
        evdev_type = 'consumer'
    else:
        press_key = args.key
        if len(press_key) != 1:
            print("ERROR: --key must be a single character for type 'key'")
            sys.exit(1)
        if press_key not in CHAR_TO_LINUX:
            print(f"ERROR: key '{press_key}' not in CHAR_TO_LINUX mapping")
            sys.exit(1)
        expected_linux = CHAR_TO_LINUX[press_key]
        evdev_type = 'keyboard'

    release_key = to_release(press_key)
    type_label = {'key': 'Keyboard', 'mouse': 'Mouse', 'media': 'Media'}[args.type]

    # ---- Open serial (DTR/RTS low to avoid resetting the board) ----
    print(f"Serial:  {args.serial} @ {args.baud} baud")
    ser = serial.Serial()
    ser.port = args.serial
    ser.baudrate = args.baud
    ser.timeout = 1
    ser.dtr = False
    ser.rts = False
    ser.open()
    ser.reset_input_buffer()
    time.sleep(0.2)
    ser.reset_input_buffer()
    print("         OK")

    # ---- Connect WebSocket ----
    ws_url = f"ws://{args.host}:81/"
    print(f"WebSocket: {ws_url}")
    ws = create_connection(ws_url, timeout=10)
    print("           OK")

    # ---- Set up evdev HID monitor ----
    dev, ecodes = find_evdev_device(evdev_type)
    if dev:
        print(f"USB HID:  {dev.name} at {dev.path}")
    else:
        print("USB HID:  not found (install evdev, check permissions, plug USB)")

    # ---- Start serial reader thread ----
    q = queue.Queue()
    stop = threading.Event()
    reader = threading.Thread(target=serial_reader, args=(ser, q, stop))
    reader.start()

    # ---- Warm up: release all, flush stale data ----
    ws.send('~')
    time.sleep(0.2)
    ser.reset_input_buffer()
    for _ in range(5):
        ws.send(press_key)
        time.sleep(0.1)
        ws.send(release_key)
        time.sleep(0.15)
    ser.reset_input_buffer()
    while not q.empty():
        q.get_nowait()
    time.sleep(0.3)

    # ---- Measure ----
    fw_times = []
    hid_times = []
    print(f"\nMeasuring {args.samples}x {type_label} '{press_key}'...\n")

    for i in range(args.samples):
        ser.reset_input_buffer()
        while not q.empty():
            q.get_nowait()

        t_send = time.monotonic_ns()
        ws.send(press_key)

        if args.type == 'media':
            t_hid_arrival = wait_for_hid_event(dev, expected_linux)
        else:
            t_hid_arrival = wait_for_hid_key(dev, expected_linux)

        timing = None
        try:
            timing = q.get(timeout=1.0)
        except queue.Empty:
            pass

        ws.send(release_key)

        if timing is not None:
            fw_times.append(timing['fw_us'])
        if t_hid_arrival is not None:
            hid_us = (t_hid_arrival - t_send) / 1000
            hid_times.append(hid_us)
            hid_str = f"  hid={hid_us:7.0f}us"
        else:
            hid_str = "  (no hid)"

        fw_str = f"fw={timing['fw_us']:3d}us" if timing else "fw=---"
        print(f"  [{i+1:3d}/{args.samples}] {fw_str}{hid_str}")

        time.sleep(args.interval)

    # ---- Cleanup ----
    stop.set()
    reader.join(timeout=2)
    ser.close()
    ws.close()
    if dev:
        dev.close()

    # ---- Report ----
    def stats(label, values, unit='us'):
        if not values:
            return
        values.sort()
        n = len(values)
        mean = sum(values) / n
        median = values[n // 2]
        print(f"\n{label}:")
        print(f"  Samples: {n}")
        print(f"  Mean:    {mean:9.1f} {unit}")
        print(f"  Median:  {median:9.1f} {unit}")
        print(f"  Min:     {min(values):9.1f} {unit}")
        print(f"  Max:     {max(values):9.1f} {unit}")
        if n > 1:
            variance = sum((x - mean) ** 2 for x in values) / (n - 1)
            print(f"  Stdev:   {variance ** 0.5:9.1f} {unit}")

    print("\n" + "=" * 45)
    print(f"LATENCY RESULTS — {type_label}")
    print("=" * 45)
    stats("Firmware processing (WS recv -> HID send)", fw_times)
    if hid_times:
        stats("End-to-end via evdev (WS send -> HID press on host)", hid_times)
    else:
        print("\nEnd-to-end via evdev: no data")
    print()


if __name__ == '__main__':
    main()
