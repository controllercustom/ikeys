"""Build + serial-upload the iKeys sketch and discover the board's control
address (WebSocket port 81), so the end-to-end harness can reach the board
without manual network configuration.

Discovery strategy (most reliable first):
  * explicit host (IKEYS_HOST / --ikey-host)
  * after a flash: scan the LAN for port 81 and confirm the "iKeys" WS
    greeting (this verifies it really is an iKeys board and avoids the
    race of catching the UART boot line)
  * UART boot-log IP scrape (best-effort, may miss the line)
  * mDNS `ikeys.local`
"""
import ipaddress
import os
import re
import socket
import subprocess
import threading
import time
from pathlib import Path

SKETCH_DIR = Path(os.environ.get("IKEYS_SKETCH_DIR", Path(__file__).resolve().parents[2]))
DEFAULT_FQBN = "esp32:esp32:esp32s3:USBMode=default,CDCOnBoot=default"
DEFAULT_PORT = "/dev/ttyUSB0"

IP_RE = re.compile(r"IP=([\d.]+)")


def build_and_upload(port=DEFAULT_PORT, fqbn=DEFAULT_FQBN, sketch_dir=SKETCH_DIR):
    """Compile and serial-upload the sketch. Returns True on success."""
    cmd = ["arduino-cli", "compile", "-u", "-p", port, "--fqbn", fqbn, str(sketch_dir)]
    res = subprocess.run(cmd)
    return res.returncode == 0


def discover_ip_from_serial(port=DEFAULT_PORT, timeout=25):
    """Open the board's UART and capture the WiFi IP from the boot log.

    Best-effort: the board prints its IP only once at boot, so this can miss
    the line if the port is opened too late. Prefer discover_board_on_lan().
    """
    import serial  # imported lazily so test collection never requires pyserial

    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with serial.Serial(port, 115200, timeout=1.0) as ser:
                ser.reset_input_buffer()
                while time.time() < deadline:
                    line = ser.readline().decode(errors="ignore").strip()
                    m = IP_RE.search(line)
                    if m:
                        return m.group(1)
        except (OSError, serial.SerialException):
            time.sleep(1.0)
    return None


def _local_subnets():
    """Return [(network_str, prefix), ...] for non-loopback IPv4 interfaces."""
    try:
        out = subprocess.run(["ip", "-o", "-4", "addr", "show"],
                             capture_output=True, text=True, timeout=5).stdout
    except Exception:
        out = ""
    subs = []
    for line in out.splitlines():
        parts = line.split()
        if "inet" not in parts:
            continue
        addr = parts[parts.index("inet") + 1]  # e.g. 192.168.1.185/24
        ip, _, prefix = addr.partition("/")
        if ip.startswith("127."):
            continue
        try:
            subs.append((ip, int(prefix)))
        except ValueError:
            continue
    if not subs:
        # Fallback: assume a /24 on whatever the hostname resolves to.
        try:
            ip = socket.gethostbyname(socket.gethostname())
            if not ip.startswith("127."):
                subs.append((ip, 24))
        except Exception:
            pass
    return subs


def _hosts_in_subnet(ip, prefix):
    net = ipaddress.ip_network(f"{ip}/{prefix}", strict=False)
    return [str(h) for h in net.hosts()]


def discover_board_on_lan(scan_timeout=20):
    """Scan local subnets for port 81, then verify the iKeys WS greeting.

    Returns the board IP, or None if not found.
    """
    import websocket  # lazy: only needed when actually discovering

    subs = _local_subnets()
    open_hosts = []

    def tcp_check(ip):
        s = socket.socket()
        s.settimeout(0.25)
        try:
            s.connect((ip, 81))
            open_hosts.append(ip)
        except Exception:
            pass
        finally:
            s.close()

    threads = [threading.Thread(target=tcp_check, args=(h,), daemon=True)
               for (ip, prefix) in subs for h in _hosts_in_subnet(ip, prefix)]
    if not threads:
        return None
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=scan_timeout)

    for ip in open_hosts:
        try:
            ws = websocket.create_connection(f"ws://{ip}:81", timeout=2)
            ws.settimeout(2)
            try:
                greeting = ws.recv() or ""
            except Exception:
                greeting = ""
            ws.close()
            if "iKeys" in str(greeting):
                return ip
        except Exception:
            continue
    return None
