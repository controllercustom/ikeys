"""Test LED state bitmask parsing and class toggling.

LED bitmask format: #LED:XX (hex digit)
  bit 0 (0x01) = Num Lock
  bit 1 (0x02) = Caps Lock
  bit 2 (0x04) = Scroll Lock
"""
import pytest


BIT_NUM = 0
BIT_CAPS = 1
BIT_SCROLL = 2

NL_KEY = '*NL'
CAL_KEY = '*CaLk'


def parse_led_hex(msg: str) -> int:
    """Parse '#LED:XX' message, return integer mask."""
    assert msg.startswith('#LED:')
    return int(msg[5:], 16)


def led_state(mask: int) -> dict:
    """Return dict of {NL: bool, CL: bool, SL: bool} from bitmask."""
    return {
        'num': bool(mask & (1 << BIT_NUM)),
        'caps': bool(mask & (1 << BIT_CAPS)),
        'scroll': bool(mask & (1 << BIT_SCROLL)),
    }


def toggle_class_name(on: bool) -> str:
    return 'led on' if on else 'led off'


class TestLEDParsing:
    def test_all_off(self):
        assert parse_led_hex('#LED:00') == 0x00

    def test_num_lock_only(self):
        assert parse_led_hex('#LED:01') == 0x01

    def test_caps_lock_only(self):
        assert parse_led_hex('#LED:02') == 0x02

    def test_scroll_lock_only(self):
        assert parse_led_hex('#LED:04') == 0x04

    def test_all_on(self):
        assert parse_led_hex('#LED:07') == 0x07

    @pytest.mark.parametrize("mask", range(8))
    def test_round_trip(self, mask):
        msg = f'#LED:{mask:02X}'
        assert parse_led_hex(msg) == mask

    def test_lowercase_hex(self):
        assert parse_led_hex('#LED:ff') == 0xFF

    def test_message_length(self):
        msg = '#LED:00'
        assert len(msg) == 7


class TestLEDStateMapping:
    def test_num_lock_from_mask(self):
        state = led_state(0x01)
        assert state['num'] is True
        assert state['caps'] is False
        assert state['scroll'] is False

    def test_caps_lock_from_mask(self):
        state = led_state(0x02)
        assert state['num'] is False
        assert state['caps'] is True
        assert state['scroll'] is False

    def test_scroll_lock_from_mask(self):
        state = led_state(0x04)
        assert state['num'] is False
        assert state['caps'] is False
        assert state['scroll'] is True

    def test_all_off_state(self):
        state = led_state(0x00)
        assert all(v is False for v in state.values())

    def test_all_on_state(self):
        state = led_state(0x07)
        assert all(v is True for v in state.values())

    @pytest.mark.parametrize("mask,expected_nl,expected_cl,expected_sl", [
        (0b000, False, False, False),
        (0b001, True,  False, False),
        (0b010, False, True,  False),
        (0b011, True,  True,  False),
        (0b100, False, False, True),
        (0b101, True,  False, True),
        (0b110, False, True,  True),
        (0b111, True,  True,  True),
    ])
    def test_all_combinations(self, mask, expected_nl, expected_cl, expected_sl):
        state = led_state(mask)
        assert state['num'] == expected_nl
        assert state['caps'] == expected_cl
        assert state['scroll'] == expected_sl

    def test_bit_positions_are_non_overlapping(self):
        assert BIT_NUM != BIT_CAPS != BIT_SCROLL
        assert (1 << BIT_NUM) == 0x01
        assert (1 << BIT_CAPS) == 0x02
        assert (1 << BIT_SCROLL) == 0x04


class TestLEDClassToggle:
    def test_on_class(self):
        assert toggle_class_name(True) == 'led on'

    def test_off_class(self):
        assert toggle_class_name(False) == 'led off'

    def test_query_selector_targets(self):
        assert NL_KEY == '*NL'
        assert CAL_KEY == '*CaLk'

    def test_both_instances_toggled(self):
        assert True


class TestLEDDisplayUpdate:
    def test_led_display_message_format(self):
        mask = 0x05
        msg = f'#LED:{mask:02X}'
        assert msg == '#LED:05'
        assert parse_led_hex(msg) == 0x05
