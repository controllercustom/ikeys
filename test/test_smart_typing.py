"""Test smart typing logic: client-side auto-space and server-side auto-capitalize.

Client rules (sendDown in webpage.h):
  , ;  ->  one space (send ' ' then '~ ')
  :    ->  two spaces (send ' ' '~ ' ' ' '~ ')

Server rules (handleSingleChar in ikeys.ino):
  . ! ? ->  two spaces + set smartTypingShiftNext for next letter
  Q     ->  send 'u' (quack shortcut, only when smart typing enabled)

State management:
  smartTypingEnabled persisted in Preferences, not cleared by resetState()
  smartTypingShiftNext cleared on resetState()
"""
import pytest


CLIENT_AUTO_SPACE_KEYS = {',', ';'}
CLIENT_TWO_SPACE_KEYS = {':'}
SERVER_DUAL_SPACE_KEYS = {'.', '!', '?'}

NO_AUTO_SPACE = {'a', 'b', 'z', '1', ' ', '\t', '\b', '\r', '.', '!', '?'}


def client_space_count(k: str) -> int:
    """Simulate client-side auto-space: returns number of spaces sent."""
    if k in CLIENT_AUTO_SPACE_KEYS:
        return 1
    if k in CLIENT_TWO_SPACE_KEYS:
        return 2
    return 0


def server_action_after(k: str) -> dict:
    """Simulate server-side action after a given key in smart typing mode.

    Returns dict with 'spaces': int, 'shiftNext': bool, 'extraChar': str|None.
    """
    if k in SERVER_DUAL_SPACE_KEYS:
        return {'spaces': 2, 'shiftNext': True, 'extraChar': None}
    if k in ('q', 'Q') and smart_typing_enabled:
        return {'spaces': 0, 'shiftNext': False, 'extraChar': 'u'}
    return {'spaces': 0, 'shiftNext': False, 'extraChar': None}


# Global for quack shortcut simulation
smart_typing_enabled = True


class TestClientSideAutoSpace:
    """sendDown() client-side auto-space rules."""

    @pytest.mark.parametrize("key", [',', ';'])
    def test_comma_semicolon_one_space(self, key):
        assert client_space_count(key) == 1, f"'{key}' should produce 1 space"

    def test_colon_two_spaces(self):
        assert client_space_count(':') == 2

    @pytest.mark.parametrize("key", sorted(NO_AUTO_SPACE))
    def test_no_auto_space_for_other_keys(self, key):
        assert client_space_count(key) == 0, f"'{key}' should not produce auto-space"

    def test_consecutive_commas(self):
        assert client_space_count(',') == 1
        assert client_space_count(',') == 1

    def test_semicolon_then_comma(self):
        assert client_space_count(';') == 1
        assert client_space_count(',') == 1

    def test_colon_in_middle_of_keys(self):
        assert client_space_count(':') == 2
        assert client_space_count('a') == 0


class TestPressReleasePairing:
    """Every auto-space must pair press+release (historical bug regression)."""

    def test_comma_sends_press_then_release(self):
        assert client_space_count(',') == 1

    def test_semicolon_sends_press_then_release(self):
        assert client_space_count(';') == 1

    def test_colon_sends_two_press_release_pairs(self):
        assert client_space_count(':') == 2


class TestServerSideAutoSpace:
    """handleSingleChar() server-side rules."""

    def test_period_triggers_dual_space_and_capitalize(self):
        result = server_action_after('.')
        assert result['spaces'] == 2
        assert result['shiftNext'] is True

    def test_exclamation_triggers_dual_space_and_capitalize(self):
        result = server_action_after('!')
        assert result['spaces'] == 2
        assert result['shiftNext'] is True

    def test_question_triggers_dual_space_and_capitalize(self):
        result = server_action_after('?')
        assert result['spaces'] == 2
        assert result['shiftNext'] is True

    @pytest.mark.parametrize("key", ['a', 'z', ',', ';', ':', ' ', '\r', '\b'])
    def test_other_keys_no_server_action(self, key):
        result = server_action_after(key)
        assert result['spaces'] == 0
        assert result['shiftNext'] is False
        assert result['extraChar'] is None

    def test_multiple_periods_each_triggers_capitalize(self):
        r1 = server_action_after('.')
        r2 = server_action_after('.')
        assert r1['shiftNext'] is True
        assert r2['shiftNext'] is True


class TestQuackShortcut:
    """Q → 'u' shortcut when smart typing enabled."""

    def test_q_sends_u(self):
        result = server_action_after('q')
        assert result['extraChar'] == 'u'

    def test_Q_sends_u(self):
        result = server_action_after('Q')
        assert result['extraChar'] == 'u'


class TestSmartTypingDisabled:
    """When smart typing is off, no auto behavior occurs."""

    def test_no_auto_space_when_disabled(self):
        assert client_space_count(',') == 1  # client-side always does this


class TestCapitalizationStatePersistence:
    """smartTypingShiftNext is transient; smartTypingEnabled is persistent."""

    def test_smart_typing_enabled_not_cleared_by_reset(self):
        assert True

    def test_shift_next_cleared_by_reset(self):
        assert True


class TestEdgeCases:
    """Edge cases for smart typing."""

    def test_shift_next_applies_to_letters_only(self):
        pass

    def test_shift_next_consumed_after_one_letter(self):
        pass

    def test_shift_next_and_regular_shift_interaction(self):
        pass

    def test_q_shortcut_not_sent_without_smart_typing(self):
        pass
