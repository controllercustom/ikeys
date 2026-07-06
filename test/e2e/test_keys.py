"""End-to-end key tests: send a key over WebSocket, assert the exact evdev
press + release the board's USB HID produces. This exercises the real
dispatch path in ikeys.ino (including the PgUp/PgDn/Insert regression)."""
import time

import pytest
from evdev import ecodes

from .hid_mapping import SINGLE_CHAR_TO_EVDEV, NAMED_KEY_TO_EVDEV


def _tap(ws, key, hold=0.08):
    ws.send(key)
    time.sleep(hold)
    ws.send("~" + key)


KEY_CASES = []
for _k, _c in SINGLE_CHAR_TO_EVDEV.items():
    KEY_CASES.append((_k, _c))
for _k, _c in NAMED_KEY_TO_EVDEV.items():
    KEY_CASES.append((_k, _c))


@pytest.mark.e2e
@pytest.mark.parametrize("key,code", KEY_CASES,
                         ids=lambda v: str(v[0]) if isinstance(v, (tuple, list)) else str(v))
def test_key_press_release(board_ws, hid_kb, key, code):
    _tap(board_ws, key)
    hid_kb.collect(0.6)
    assert hid_kb.saw_key(code, 1), f"no press event for {key!r} (evdev {code})"
    assert hid_kb.saw_key(code, 0), f"no release event for {key!r} (evdev {code})"


@pytest.mark.e2e
@pytest.mark.parametrize("key,code", [
    ("*PgUp", ecodes.KEY_PAGEUP),
    ("*PgDn", ecodes.KEY_PAGEDOWN),
    ("*Ins", ecodes.KEY_INSERT),
])
def test_nav_keys_not_confused(board_ws, hid_kb, key, code):
    """Regression: PgUp/PgDn/Insert must each emit its own distinct code."""
    _tap(board_ws, key)
    hid_kb.collect(0.6)
    assert hid_kb.saw_key(code, 1), f"{key} did not emit {code}"
    assert hid_kb.saw_key(code, 0)


@pytest.mark.e2e
def test_shift_plus_a(board_ws, hid_kb):
    board_ws.send("*Shft")
    time.sleep(0.05)
    board_ws.send("a")
    time.sleep(0.05)
    board_ws.send("~a")
    time.sleep(0.05)
    board_ws.send("~*Shft")
    hid_kb.collect(0.6)
    assert hid_kb.saw_key(ecodes.KEY_LEFTSHIFT, 1)
    assert hid_kb.saw_key(ecodes.KEY_A, 1)
    assert hid_kb.saw_key(ecodes.KEY_A, 0)
    assert hid_kb.saw_key(ecodes.KEY_LEFTSHIFT, 0)
