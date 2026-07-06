"""Pytest configuration and fixtures for iKeys end-to-end hardware tests.

These tests drive the board over its WebSocket control port (81) and observe
the resulting USB HID output via python-evdev on the host. They are skipped
unless explicitly selected (run `pytest test/e2e` or `pytest -m e2e`) so the
default `pytest test/` run stays 100% offline.

Requirements: python-evdev (system package) and websocket-client. The evdev
device must be grabbed, which needs root -> run with `sudo`.
"""
import os
import socket

import pytest

try:
    from evdev import InputDevice, ecodes, list_devices
    import websocket
    _DEPS_OK = True
except Exception:  # pragma: no cover - hardware deps absent
    _DEPS_OK = False
    InputDevice = ecodes = list_devices = websocket = None

# Substring used to match the board's USB HID device names (both the generic
# ESP32-S3 dev module "ESP32S3_DEV" and the M5Stack AtomS3 "M5STACK_ATOMS3").
KEYBOARD_NAME = "Keyboard"
MOUSE_NAME = "Mouse"


def pytest_addoption(parser):
    group = parser.getgroup("ikeyse2e")
    group.addoption("--ikey-host", action="store", default=None,
                    help="iKeys board IP/hostname for WebSocket control (port 81).")
    group.addoption("--ikey-flash", action="store_true", default=False,
                    help="Compile + serial-upload the sketch to /dev/ttyUSB0, then "
                         "discover the board IP from its UART boot log.")
    group.addoption("--ikey-port", action="store", default="/dev/ttyUSB0",
                    help="Serial port for flashing / boot-log IP discovery.")
    group.addoption("--ikey-fqbn", action="store",
                    default="esp32:esp32:esp32s3:USBMode=default,CDCOnBoot=default",
                    help="Board FQBN for arduino-cli.")


def pytest_configure(config):
    config.addinivalue_line("markers", "e2e: end-to-end hardware tests (need board + sudo)")


def pytest_collection_modifyitems(config, items):
    args = getattr(config, "invocation_params", None)
    args = list(args.args) if args is not None else getattr(config, "args", [])
    args_str = " ".join(str(a) for a in args)
    markexpr = getattr(config.option, "markexpr", "") or ""
    selected = ("test/e2e" in args_str) or ("e2e" in markexpr.split())
    for item in items:
        if "test/e2e" not in str(item.fspath):
            continue
        if selected and _DEPS_OK:
            continue
        reason = ("e2e hardware tests skipped; run 'pytest test/e2e -v' or '-m e2e'"
                  if _DEPS_OK else "evdev/websocket not installed (e2e requires hardware deps)")
        item.add_marker(pytest.mark.skip(reason=reason))


if not _DEPS_OK:  # pragma: no cover
    pass
else:
    from .evdev_util import EventWatcher
    from .firmware import build_and_upload, discover_ip_from_serial, discover_board_on_lan

    @pytest.fixture(scope="session")
    def ikey_host(request):
        host = os.environ.get("IKEYS_HOST") or request.config.getoption("ikey_host")
        if host:
            return host
        port = request.config.getoption("ikey_port")
        if request.config.getoption("ikey_flash"):
            fqbn = request.config.getoption("ikey_fqbn")
            if not build_and_upload(port=port, fqbn=fqbn):
                pytest.skip("arduino-cli build/upload failed; is the board in download mode?")
            ip = discover_board_on_lan() or discover_ip_from_serial(port=port)
            if ip:
                return ip
            pytest.skip("board flashed but its WebSocket was not found on the LAN; "
                        "set IKEYS_HOST or connect the board to WiFi")
        # Best-effort zero-config discovery (no flash, no explicit host).
        ip = discover_ip_from_serial(port=port, timeout=5) or discover_board_on_lan()
        if ip:
            return ip
        try:
            return socket.gethostbyname("ikeys.local")
        except Exception:
            pass
        pytest.skip("iKeys board not reachable; set IKEYS_HOST, use --ikey-flash, "
                    "or connect the host to the board's WiFi")

    @pytest.fixture
    def board_ws(ikey_host):
        url = f"ws://{ikey_host}:81"
        try:
            ws = websocket.create_connection(url, timeout=5)
        except Exception as e:
            pytest.skip(f"cannot open WebSocket {url}: {e}")
        # On connect the server pushes its current state (#SMT/#MAC/...).
        # Read the burst, then pin a deterministic state so key assertions
        # aren't perturbed by smart-typing auto-injection.
        ws.settimeout(0.4)
        messages = []
        try:
            while True:
                messages.append(ws.recv())
        except Exception:
            pass
        ws.greeting = messages[0] if messages else ""
        smt = mac = False
        for m in messages:
            if m.startswith("#SMT:"):
                smt = m.endswith("1")
            elif m.startswith("#MAC:"):
                mac = m.endswith("1")
        if smt:
            ws.send("*Smt")  # smart typing injects extra keys -> disable
        if mac:
            ws.send("*Mac")  # macOS mode off for determinism
        yield ws
        try:
            ws.close()
        except Exception:
            pass

    def _find_device(substr):
        for path in list_devices():
            try:
                d = InputDevice(path)
                if "Espressif" in d.name and substr in d.name:
                    return d
            except Exception:
                continue
        return None

    @pytest.fixture
    def hid_kb():
        dev = _find_device(KEYBOARD_NAME)
        if dev is None:
            pytest.skip(f"evdev keyboard '{KEYBOARD_NAME}' not found")
        w = EventWatcher(dev)
        try:
            w.grab()
        except Exception as e:
            pytest.skip(f"cannot grab {KEYBOARD_NAME} (need sudo?): {e}")
        yield w
        w.ungrab()
        try:
            dev.close()
        except Exception:
            pass

    @pytest.fixture
    def hid_mouse():
        dev = _find_device(MOUSE_NAME)
        if dev is None:
            pytest.skip(f"evdev mouse '{MOUSE_NAME}' not found")
        w = EventWatcher(dev)
        try:
            w.grab()
        except Exception as e:
            pytest.skip(f"cannot grab {MOUSE_NAME} (need sudo?): {e}")
        yield w
        w.ungrab()
        try:
            dev.close()
        except Exception:
            pass
