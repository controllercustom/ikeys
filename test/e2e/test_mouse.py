"""End-to-end mouse tests: send mouse control keys over WebSocket and assert
the evdev button / relative-motion events the board's USB HID mouse emits."""
import time

import pytest
from evdev import ecodes


def _tap(ws, key, hold=0.08):
    ws.send(key)
    time.sleep(hold)
    ws.send("~" + key)


@pytest.mark.e2e
def test_left_click(board_ws, hid_mouse):
    _tap(board_ws, "*Cn")
    hid_mouse.collect(0.6)
    assert hid_mouse.saw_key(ecodes.BTN_LEFT, 1), "left click should press BTN_LEFT"
    assert hid_mouse.saw_key(ecodes.BTN_LEFT, 0), "left click should release BTN_LEFT"


@pytest.mark.e2e
def test_drag_lock(board_ws, hid_mouse):
    # Engage drag lock: button is pressed and held until the next tap.
    _tap(board_ws, "*RClk")
    hid_mouse.collect(0.5)
    assert hid_mouse.saw_key(ecodes.BTN_LEFT, 1), "drag lock should press left button"
    assert not hid_mouse.saw_key(ecodes.BTN_LEFT, 0), "drag lock should keep button held"
    # Disengage: second tap releases it.
    _tap(board_ws, "*RClk")
    hid_mouse.collect(0.5)
    assert hid_mouse.saw_key(ecodes.BTN_LEFT, 0), "second tap should release drag lock"


@pytest.mark.e2e
def test_move_left_emits_negative_rel_x(board_ws, hid_mouse):
    board_ws.send("*MLt")
    time.sleep(0.3)
    board_ws.send("~*MLt")
    hid_mouse.collect(0.4)
    assert hid_mouse.saw_rel(ecodes.REL_X, negative=True), \
        "holding left should emit negative REL_X motion"
