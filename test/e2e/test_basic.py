import pytest
from evdev import ecodes


@pytest.mark.e2e
def test_ws_greeting(board_ws):
    greeting = getattr(board_ws, "greeting", "") or ""
    assert "iKeys" in greeting, f"expected 'Connected to iKeys HID' greeting, got {greeting!r}"


@pytest.mark.e2e
def test_keyboard_device_present(hid_kb):
    # The fixture only yields a device whose name matched KEYBOARD_NAME; verify
    # it actually exposes key events (not just the name string).
    assert ecodes.EV_KEY in hid_kb.device.capabilities()


@pytest.mark.e2e
def test_mouse_device_present(hid_mouse):
    assert ecodes.EV_REL in hid_mouse.device.capabilities()
