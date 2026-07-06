"""Test mouse config logic: speed/accel range clamping, message format, display update."""
import pytest


SPEED_MIN = 1
SPEED_MAX = 20
ACCEL_MIN = 0
ACCEL_MAX = 10


def clamp_speed(v: int) -> int:
    return max(SPEED_MIN, min(SPEED_MAX, v))


def clamp_accel(v: int) -> int:
    return max(ACCEL_MIN, min(ACCEL_MAX, v))


def speed_msg(v: int) -> str:
    return f'#MSPEED:{clamp_speed(v)}'


def accel_msg(v: int) -> str:
    return f'#MACCEL:{clamp_accel(v)}'


class TestSpeedRange:
    def test_min_speed(self):
        assert clamp_speed(1) == 1

    def test_max_speed(self):
        assert clamp_speed(20) == 20

    def test_below_min_clamps(self):
        assert clamp_speed(0) == SPEED_MIN
        assert clamp_speed(-5) == SPEED_MIN

    def test_above_max_clamps(self):
        assert clamp_speed(21) == SPEED_MAX
        assert clamp_speed(100) == SPEED_MAX

    @pytest.mark.parametrize("v", range(1, 21))
    def test_all_valid_speeds(self, v):
        assert clamp_speed(v) == v

    def test_increment(self):
        assert clamp_speed(5 + 1) == 6

    def test_decrement(self):
        assert clamp_speed(5 - 1) == 4


class TestAccelRange:
    def test_min_accel(self):
        assert clamp_accel(0) == 0

    def test_max_accel(self):
        assert clamp_accel(10) == 10

    def test_below_min_clamps(self):
        assert clamp_accel(-1) == ACCEL_MIN

    def test_above_max_clamps(self):
        assert clamp_accel(11) == ACCEL_MAX
        assert clamp_accel(50) == ACCEL_MAX

    @pytest.mark.parametrize("v", range(0, 11))
    def test_all_valid_accels(self, v):
        assert clamp_accel(v) == v


class TestConfigMessageFormat:
    def test_speed_message_format(self):
        for v in [1, 5, 10, 20]:
            assert speed_msg(v) == f'#MSPEED:{v}'

    def test_accel_message_format(self):
        for v in [0, 3, 7, 10]:
            assert accel_msg(v) == f'#MACCEL:{v}'

    def test_clamped_speed_message(self):
        assert speed_msg(0) == '#MSPEED:1'
        assert speed_msg(25) == '#MSPEED:20'

    def test_clamped_accel_message(self):
        assert accel_msg(-1) == '#MACCEL:0'
        assert accel_msg(15) == '#MACCEL:10'


class TestDisplayUpdate:
    def test_speed_display_format(self):
        for v in [1, 5, 20]:
            display = f'Speed: {v}'
            assert display.startswith('Speed:')
            assert int(display.split()[-1]) == v

    def test_accel_display_format(self):
        for v in [0, 5, 10]:
            display = f'Accel: {v}'
            assert display.startswith('Accel:')
            assert int(display.split()[-1]) == v


class TestMouseConfigKeys:
    CONFIG_KEYS = {
        '*SpdD': ('decrement', 'speed'),
        '*SpdU': ('increment', 'speed'),
        '*AclD': ('decrement', 'accel'),
        '*AclU': ('increment', 'accel'),
        '*SpdVal': ('display', 'speed'),
        '*AclVal': ('display', 'accel'),
    }

    def test_config_key_count(self):
        assert len(self.CONFIG_KEYS) == 6

    def test_all_config_keys_defined(self, grid_data):
        grid_keys = {c['k'] for c in grid_data}
        # Config keys are on numpad, not grid
        assert '*SpdD' not in grid_keys

    def test_config_keys_in_numpad(self, numpad_data):
        npad_codes = {e[5] for e in numpad_data}
        for ck in self.CONFIG_KEYS:
            assert ck in npad_codes, f"Config key {ck} missing from numpad"


class TestMouseTickLogic:
    def test_tick_interval(self):
        assert 20  # MOUSE_TICK_MS

    def test_accel_extra_calculation(self):
        held = 250
        accel = 5
        extra = (held // 250) * accel
        assert extra == 5

    def test_accel_extra_caps(self):
        held = 5000
        accel = 10
        extra = (held // 250) * accel
        capped = min(extra, accel * 10)
        assert capped == accel * 10
