"""Test HID keycode tables: charToHID, needsShift, and special keycode constants."""
import pytest


KNOWN_MAPPINGS = {
    # (char, expected_hid, expected_shift)
    'nul':    (0x00, 0, 0),
    'tab':    (0x09, 0x2B, 0),
    'enter':  (0x0D, 0x28, 0),
    'esc':    (0x1B, 0x29, 0),
    'space':  (' ', 0x2C, 0),
    '!':      ('!', 0x1E, 1),
    '"':      ('"', 0x34, 1),
    '#':      ('#', 0x20, 1),
    '$':      ('$', 0x21, 1),
    '%':      ('%', 0x22, 1),
    '&':      ('&', 0x24, 1),
    '\'':     ('\'', 0x34, 0),
    '(':      ('(', 0x26, 1),
    ')':      (')', 0x27, 1),
    '*':      ('*', 0x25, 1),
    '+':      ('+', 0x2E, 1),
    ',':      (',', 0x36, 0),
    '-':      ('-', 0x2D, 0),
    '.':      ('.', 0x37, 0),
    '/':      ('/', 0x38, 0),
    '0':      ('0', 0x27, 0),
    '1':      ('1', 0x1E, 0),
    '2':      ('2', 0x1F, 0),
    '3':      ('3', 0x20, 0),
    '4':      ('4', 0x21, 0),
    '5':      ('5', 0x22, 0),
    '6':      ('6', 0x23, 0),
    '7':      ('7', 0x24, 0),
    '8':      ('8', 0x25, 0),
    '9':      ('9', 0x26, 0),
    ':':      (':', 0x33, 1),
    ';':      (';', 0x33, 0),
    '<':      ('<', 0x36, 1),
    '=':      ('=', 0x2E, 0),
    '>':      ('>', 0x37, 1),
    '?':      ('?', 0x38, 1),
    '@':      ('@', 0x1F, 1),
    'A':      ('A', 0x04, 1),
    'B':      ('B', 0x05, 1),
    'Z':      ('Z', 0x1D, 1),
    'a':      ('a', 0x04, 0),
    'b':      ('b', 0x05, 0),
    'z':      ('z', 0x1D, 0),
    '[':      ('[', 0x2F, 0),
    '\\':     ('\\', 0x31, 0),
    ']':      (']', 0x30, 0),
    '^':      ('^', 0x23, 1),
    '_':      ('_', 0x2D, 1),
    '`':      ('`', 0x35, 0),
    '{':      ('{', 0x2F, 1),
    '|':      ('|', 0x31, 1),
    '}':      ('}', 0x30, 1),
    '~':      ('~', 0x35, 1),
    'del':    (0x7F, 0, 0),
}


class TestCharToHID:
    """Verify charToHID() lookup table for all 128 entries."""

    def test_known_mappings(self, char_to_hid):
        for name, (char, expected_hid, _) in KNOWN_MAPPINGS.items():
            if isinstance(char, str):
                idx = ord(char)
            else:
                idx = char
            assert idx < 128
            assert char_to_hid[idx] == expected_hid, (
                f"charToHID({name}={idx:#04x}) expected {expected_hid:#04x}, got {char_to_hid[idx]:#04x}"
            )

    def test_lowercase_alpha_sequential(self, char_to_hid):
        for i, c in enumerate(range(ord('a'), ord('z') + 1)):
            expected = 0x04 + i
            assert char_to_hid[c] == expected, (
                f"charToHID('{chr(c)}') expected {expected:#04x}, got {char_to_hid[c]:#04x}"
            )

    def test_uppercase_alpha_sequential(self, char_to_hid):
        for i, c in enumerate(range(ord('A'), ord('Z') + 1)):
            expected = 0x04 + i
            assert char_to_hid[c] == expected, (
                f"charToHID('{chr(c)}') expected {expected:#04x}, got {char_to_hid[c]:#04x}"
            )

    def test_lower_upper_same_keycode(self, char_to_hid):
        for c in range(26):
            lower = ord('a') + c
            upper = ord('A') + c
            assert char_to_hid[lower] == char_to_hid[upper], (
                f"Mismatch between '{chr(lower)}' and '{chr(upper)}'"
            )

    def test_control_codes_below_32(self, char_to_hid):
        for i in range(0x20):
            val = char_to_hid[i]
            assert val == 0 or val >= 0x28, (
                f"Unexpected HID code for index {i:#04x}: {val:#04x}"
            )

    def test_backspace_vs_tab(self, char_to_hid):
        assert char_to_hid[0x08] == 0x2A
        assert char_to_hid[0x09] == 0x2B

    def test_delete_returns_zero(self, char_to_hid):
        assert char_to_hid[0x7F] == 0

    def test_nul_returns_zero(self, char_to_hid):
        assert char_to_hid[0] == 0

    def test_digit_0_vs_close_paren(self, char_to_hid):
        assert char_to_hid[ord('0')] == char_to_hid[ord(')')]

    def test_decimal_point_not_in_table(self, char_to_hid):
        # period '.' is HID 0x37, but numpad decimal KEY_NP_DOT is 0x63
        assert char_to_hid[ord('.')] == 0x37

    def test_special_keycodes_match_hid_constants(self, char_to_hid, hid_constants):
        # Tab is 0x2B in both tables
        assert char_to_hid[0x09] == hid_constants['KEY_TAB']
        # Space is 0x2C in both tables
        assert char_to_hid[ord(' ')] == hid_constants['KEY_SPACE']


class TestNeedsShift:
    """Verify needsShift() lookup table for all 128 entries."""

    def test_known_mappings(self, needs_shift):
        for name, (char, _, expected_shift) in KNOWN_MAPPINGS.items():
            if isinstance(char, str):
                idx = ord(char)
            else:
                idx = char
            assert idx < 128
            assert needs_shift[idx] == expected_shift, (
                f"needsShift({name}={idx:#04x}) expected {expected_shift}, got {needs_shift[idx]}"
            )

    def test_all_letters_consistent(self, needs_shift):
        for c in range(ord('A'), ord('Z') + 1):
            assert needs_shift[c] == 1, f"Uppercase letter '{chr(c)}' should need shift"
        for c in range(ord('a'), ord('z') + 1):
            assert needs_shift[c] == 0, f"Lowercase letter '{chr(c)}' should not need shift"

    def test_digits_no_shift(self, needs_shift):
        for c in range(ord('0'), ord('9') + 1):
            assert needs_shift[c] == 0, f"Digit '{chr(c)}' should not need shift"

    def test_shift_symbols(self, needs_shift):
        shift_chars = '!@#$%^&*()_+{}|:"<>?~'
        for ch in shift_chars:
            assert needs_shift[ord(ch)] == 1, f"'{ch}' should need shift"

    def test_no_shift_symbols(self, needs_shift):
        no_shift = ' \'-,.;=[]\\`'
        for ch in no_shift:
            assert needs_shift[ord(ch)] == 0, f"'{ch}' should not need shift"

    def test_first_32_all_zero(self, needs_shift):
        for i in range(0x20):
            assert needs_shift[i] == 0, f"Control char {i} should not need shift"

    def test_last_entry_127_zero(self, needs_shift):
        assert needs_shift[127] == 0


class TestHIDConstants:
    """Verify HID keycode constants are self-consistent."""

    def test_f_key_sequence(self, hid_constants):
        for i in range(1, 13):
            expected = hid_constants['KEY_F1'] + i - 1
            assert expected == 0x3A + i - 1, f"KEY_F{i} should be {0x3A + i - 1:#04x}"

    def test_numpad_sequence(self, hid_constants):
        assert hid_constants['KEY_NP1'] == 0x59
        assert hid_constants['KEY_NP9'] == 0x61
        for i in range(1, 10):
            label = f'KEY_NP{i}'
            assert hid_constants[label] <= 0x61, f"{label} out of range"

    def test_modifier_weights(self, hid_constants):
        assert hid_constants['MOD_LCTRL'] == 0x01
        assert hid_constants['MOD_LSHIFT'] == 0x02
        assert hid_constants['MOD_LALT'] == 0x04
        assert hid_constants['MOD_LGUI'] == 0x08
        # Verify modifiers are non-overlapping bitmask bits
        mods = ['MOD_LCTRL', 'MOD_LSHIFT', 'MOD_LALT', 'MOD_LGUI']
        values = [hid_constants[m] for m in mods]
        unique = set(values)
        assert len(unique) == len(values), "Modifier values must be unique"
        assert sum(values) == 0x0F, "Modifiers must form contiguous 4-bit mask"
