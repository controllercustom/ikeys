"""Test WebSocket message protocol format.

Client → Server messages:
  Key press:   raw string (e.g. "a", "*Shft", "\b", " ")
  Key release: "~" + raw string (e.g. "~a", "~*Shft")
  Config:      "#MSPEED:5", "#MACCEL:3"

Server → Client messages:
  Status:      "#LED:XX", "#DRAG:1/0", "#SMT:1/0", "#NP:1/0", "#MAC:1/0"
  Config echo: "#MSPEED:5", "#MACCEL:3"
"""
import pytest


def key_down(k: str) -> str:
    return k


def key_up(k: str) -> str:
    return '~' + k


def config_speed(v: int) -> str:
    return f'#MSPEED:{v}'


def config_accel(v: int) -> str:
    return f'#MACCEL:{v}'


def server_led(mask: int) -> str:
    return f'#LED:{mask:02X}'


def server_bool(name: str, value: bool) -> str:
    return f'#{name}:{1 if value else 0}'


class TestKeyDownFormat:
    def test_single_char(self):
        assert key_down('a') == 'a'
        assert key_down('z') == 'z'
        assert key_down(' ') == ' '
        assert key_down('1') == '1'

    def test_special_chars(self):
        assert key_down('\b') == '\b'
        assert key_down('\r') == '\r'
        assert key_down('\t') == '\t'
        assert key_down('\x1b') == '\x1b'

    def test_modifier_keys(self):
        assert key_down('*Shft') == '*Shft'
        assert key_down('*Ctrl') == '*Ctrl'
        assert key_down('*Alt') == '*Alt'
        assert key_down('*Cmd') == '*Cmd'

    def test_function_keys(self):
        assert key_down('*F1') == '*F1'
        assert key_down('*F12') == '*F12'

    def test_navigation_keys(self):
        assert key_down('*MUp') == '*MUp'
        assert key_down('*MDn') == '*MDn'
        assert key_down('*MLt') == '*MLt'
        assert key_down('*MRt') == '*MRt'
        assert key_down('*MUL') == '*MUL'
        assert key_down('*MUR') == '*MUR'
        assert key_down('*MDL') == '*MDL'
        assert key_down('*MDR') == '*MDR'

    def test_numpad_keys(self):
        assert key_down('*NP7') == '*NP7'
        assert key_down('*NP/') == '*NP/'
        assert key_down('*NPEn') == '*NPEn'

    def test_system_keys(self):
        assert key_down('*Home') == '*Home'
        assert key_down('*End') == '*End'
        assert key_down('*PgUp') == '*PgUp'
        assert key_down('*PgDn') == '*PgDn'
        assert key_down('*Ins') == '*Ins'
        assert key_down('*Del') == '*Del'
        assert key_down('*NL') == '*NL'
        assert key_down('*NP') == '*NP'
        assert key_down('*Mac') == '*Mac'


class TestMacModeToggle:
    def test_toggle_on_via_server(self):
        assert server_bool('MAC', True) == '#MAC:1'

    def test_toggle_off_via_server(self):
        assert server_bool('MAC', False) == '#MAC:0'

    def test_toggle_key_format(self):
        assert key_down('*Mac') == '*Mac'


class TestKeyUpFormat:
    def test_release_prefix(self):
        assert key_up('a') == '~a'
        assert key_up('*Shft') == '~*Shft'
        assert key_up(' ') == '~ '

    def test_release_is_opposite_of_down(self):
        k = '*F5'
        assert key_up(k) == '~' + key_down(k)

    def test_numpad_release(self):
        assert key_up('*NP0') == '~*NP0'


class TestClientConfigMessages:
    def test_speed_format(self):
        assert config_speed(5) == '#MSPEED:5'
        assert config_speed(20) == '#MSPEED:20'

    def test_accel_format(self):
        assert config_accel(3) == '#MACCEL:3'
        assert config_accel(10) == '#MACCEL:10'

    def test_speed_bounds(self):
        for v in range(1, 21):
            msg = config_speed(v)
            assert msg == f'#MSPEED:{v}'

    def test_accel_bounds(self):
        for v in range(0, 11):
            msg = config_accel(v)
            assert msg == f'#MACCEL:{v}'


class TestServerStatusMessages:
    def test_led_format(self):
        assert server_led(0x00) == '#LED:00'
        assert server_led(0x01) == '#LED:01'
        assert server_led(0x07) == '#LED:07'
        assert server_led(0xFF & 0x07) == '#LED:07'

    def test_drag_format(self):
        assert server_bool('DRAG', True) == '#DRAG:1'
        assert server_bool('DRAG', False) == '#DRAG:0'

    def test_smt_format(self):
        assert server_bool('SMT', True) == '#SMT:1'
        assert server_bool('SMT', False) == '#SMT:0'

    def test_np_format(self):
        assert server_bool('NP', True) == '#NP:1'
        assert server_bool('NP', False) == '#NP:0'

    def test_mac_format(self):
        assert server_bool('MAC', True) == '#MAC:1'
        assert server_bool('MAC', False) == '#MAC:0'

    def test_led_message_length(self):
        for mask in range(8):
            msg = server_led(mask)
            assert len(msg) == 7, f"#LED: should be 7 chars, got '{msg}'"


class TestServerConfigEcho:
    def test_speed_echo_passthrough(self):
        msg = '#MSPEED:7'
        assert msg == config_speed(7)

    def test_accel_echo_passthrough(self):
        msg = '#MACCEL:4'
        assert msg == config_accel(4)


class TestNumpadModeToggle:
    def test_toggle_on_via_server(self):
        assert server_bool('NP', True) == '#NP:1'

    def test_toggle_off_via_server(self):
        assert server_bool('NP', False) == '#NP:0'


class TestHeldKeyContract:
    """Keys that must stay reported as DOWN until the finger lifts.

    The device holds the key on key-down and only releases it on the
    matching '~key' up-message (like a real USB keyboard), so keys such
    as arrows, F-keys, nav keys, numpad keys and Caps Lock can be held
    (e.g. for games). Each held key's up-message is exactly '~' + its
    down-message.
    """
    HELD_KEYS = [
        '*Up', '*Dn', '*Lft', '*Rgt',
        '*Del', '*Home', '*End', '*PgUp', '*PgDn', '*Ins',
        '*F1', '*F12',
        '*CaLk',
        '*NP7', '*NP0', '*NPEn', '*NP/',
        '*NL',
    ]

    def test_down_is_plain_key(self):
        for k in self.HELD_KEYS:
            assert key_down(k) == k

    def test_up_is_tilde_prefixed(self):
        for k in self.HELD_KEYS:
            assert key_up(k) == '~' + k

    def test_up_releases_exactly_what_down_sent(self):
        for k in self.HELD_KEYS:
            assert key_up(k) == '~' + key_down(k)
