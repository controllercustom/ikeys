"""Shared fixtures for iKeys test suite."""
import pytest


@pytest.fixture
def char_to_hid():
    """charToHID lookup table (indices 0-127, matching ikeys.ino:181-195)."""
    return bytes([
        0,0,0,0,0,0,0,0, 0x2A,0x2B,0x28,0,0,0x28,0,0,
        0,0,0,0,0,0,0,0, 0,0,0,0x29,0,0,0,0,
        0x2C,0x1E,0x34,0x20, 0x21,0x22,0x24,0x34,
        0x26,0x27,0x25,0x2E, 0x36,0x2D,0x37,0x38,
        0x27,0x1E,0x1F,0x20, 0x21,0x22,0x23,0x24,
        0x25,0x26,0x33,0x33, 0x36,0x2E,0x37,0x38,
        0x1F,0x04,0x05,0x06, 0x07,0x08,0x09,0x0A,
        0x0B,0x0C,0x0D,0x0E, 0x0F,0x10,0x11,0x12,
        0x13,0x14,0x15,0x16, 0x17,0x18,0x19,0x1A,
        0x1B,0x1C,0x1D,0x2F, 0x31,0x30,0x23,0x2D,
        0x35,0x04,0x05,0x06, 0x07,0x08,0x09,0x0A,
        0x0B,0x0C,0x0D,0x0E, 0x0F,0x10,0x11,0x12,
        0x13,0x14,0x15,0x16, 0x17,0x18,0x19,0x1A,
        0x1B,0x1C,0x1D,0x2F, 0x31,0x30,0x35,0
    ])


@pytest.fixture
def needs_shift():
    """needsShift bool table (indices 0-127, matching ikeys.ino:201-209)."""
    return bytes([
        0,0,0,0,0,0,0,0, 0,0,0,0,0,0,0,0,
        0,0,0,0,0,0,0,0, 0,0,0,0,0,0,0,0,
        0,1,1,1,1,1,1,0, 1,1,1,1,0,0,0,0,
        0,0,0,0,0,0,0,0, 0,0,1,0,1,0,1,1,
        1,1,1,1,1,1,1,1, 1,1,1,1,1,1,1,1,
        1,1,1,1,1,1,1,1, 1,1,1,0,0,0,1,1,
        0,0,0,0,0,0,0,0, 0,0,0,0,0,0,0,0,
        0,0,0,0,0,0,0,0, 0,0,0,1,1,1,1,0
    ])


@pytest.fixture
def hid_constants():
    """HID keycode constants matching ikeys.ino:90-130."""
    return {
        'MOD_LCTRL':   0x01,
        'MOD_LSHIFT':  0x02,
        'MOD_LALT':    0x04,
        'MOD_LGUI':    0x08,
        'KEY_UP':      0x52,
        'KEY_DOWN':    0x51,
        'KEY_LEFT':    0x50,
        'KEY_RIGHT':   0x4F,
        'KEY_DELETE':  0x4C,
        'KEY_HOME':    0x4A,
        'KEY_END':     0x4D,
        'KEY_PAGE_UP':  0x4B,
        'KEY_PAGE_DOWN': 0x4E,
        'KEY_INSERT':  0x49,
        'KEY_TAB':     0x2B,
        'KEY_CAPS_LOCK': 0x39,
        'KEY_NUM_LOCK':  0x53,
        'KEY_SPACE':   0x2C,
        'KEY_F1':      0x3A,
        'KEY_NP0':     0x62,
        'KEY_NP1':     0x59,
        'KEY_NP2':     0x5A,
        'KEY_NP3':     0x5B,
        'KEY_NP4':     0x5C,
        'KEY_NP5':     0x5D,
        'KEY_NP6':     0x5E,
        'KEY_NP7':     0x5F,
        'KEY_NP8':     0x60,
        'KEY_NP9':     0x61,
        'KEY_NP_ADD':  0x57,
        'KEY_NP_SUB':  0x56,
        'KEY_NP_MUL':  0x55,
        'KEY_NP_DIV':  0x54,
        'KEY_NP_ENT':  0x58,
        'KEY_NP_DOT':  0x63,
    }


@pytest.fixture
def grid_data():
    """gridData from webpage.h:392-444, transcribed to Python list of dicts."""
    return [
        # Row 1 — System Utilities
        {'l': 'Esc',     'k': '\x1b'},
        {'l': 'Tab', 'k': '\t', 's': '*SHT'},
        {'l': '~<br>`', 'k': '`', 's': '~'},
        {'l': 'Mac Mode', 'k': '*Mac'},
        {'l': 'Num Pad', 'k': '*NP'},
        {'l': 'Insert', 'k': '*Ins'},
        {'l': 'Home', 'k': '*Home'},
        {'l': 'End', 'k': '*End'},
        {'l': 'Smart Typing', 'k': '*SmT'},
        {'l': 'PgUp', 'k': '*PgUp'},
        {'l': 'PgDn', 'k': '*PgDn'},
        {'l': 'Del', 'k': '*Del'},
        # Row 2 — Function keys
        {'l': 'F1',  'c': 'f-key', 'k': '*F1'},
        {'l': 'F2',  'c': 'f-key', 'k': '*F2'},
        {'l': 'F3',  'c': 'f-key', 'k': '*F3'},
        {'l': 'F4',  'c': 'f-key', 'k': '*F4'},
        {'l': 'F5',  'c': 'f-key', 'k': '*F5'},
        {'l': 'F6',  'c': 'f-key', 'k': '*F6'},
        {'l': 'F7',  'c': 'f-key', 'k': '*F7'},
        {'l': 'F8',  'c': 'f-key', 'k': '*F8'},
        {'l': 'F9',  'c': 'f-key', 'k': '*F9'},
        {'l': 'F10', 'c': 'f-key', 'k': '*F10'},
        {'l': 'F11', 'c': 'f-key', 'k': '*F11'},
        {'l': 'F12', 'c': 'f-key', 'k': '*F12'},
        # Row 3 — Numbers / Symbols
        {'l': '!<br>1', 'k': '1', 's': '!'},
        {'l': '@<br>2', 'k': '2', 's': '@'},
        {'l': '#<br>3', 'k': '3', 's': '#'},
        {'l': '$<br>4', 'k': '4', 's': '$'},
        {'l': '%<br>5', 'k': '5', 's': '%'},
        {'l': '^<br>6', 'k': '6', 's': '^'},
        {'l': '&<br>7', 'k': '7', 's': '&'},
        {'l': '*<br>8', 'k': '8', 's': '*'},
        {'l': '(<br>9', 'k': '9', 's': '('},
        {'l': ')<br>0', 'k': '0', 's': ')'},
        {'l': '_<br>-', 'k': '-', 's': '_'},
        {'l': '+<br>=', 'k': '=', 's': '+'},
        # Row 4 — QWERTY top
        {'l': 'Q', 'k': 'q'},
        {'l': 'W', 'k': 'w'},
        {'l': 'E', 'k': 'e'},
        {'l': 'R', 'k': 'r'},
        {'l': 'T', 'k': 't'},
        {'l': 'Y', 'k': 'y'},
        {'l': 'U', 'k': 'u'},
        {'l': 'I', 'k': 'i'},
        {'l': 'O', 'k': 'o'},
        {'l': 'P', 'k': 'p'},
        {'l': 'Backspace<br>Delete', 'span': 2, 'stack': True, 'k': '\b'},
        # Row 5 — Home row + Blue zone top
        {'l': 'A', 'k': 'a'},
        {'l': 'S', 'k': 's'},
        {'l': 'D', 'k': 'd'},
        {'l': 'F', 'k': 'f'},
        {'l': 'G', 'k': 'g'},
        {'l': 'H', 'k': 'h'},
        {'l': 'J', 'k': 'j'},
        {'l': 'K', 'k': 'k'},
        {'l': 'L', 'k': 'l'},
        {'l': '\u2196', 'c': 'nav-key', 'k': '*MUL'},
        {'l': '\u2191', 'c': 'nav-key', 'k': '*MUp'},
        {'l': '\u2197', 'c': 'nav-key', 'k': '*MUR'},
        # Row 6 — Bottom alpha + Blue zone middle
        {'l': 'Z', 'k': 'z'},
        {'l': 'X', 'k': 'x'},
        {'l': 'C', 'k': 'c'},
        {'l': 'V', 'k': 'v'},
        {'l': 'B', 'k': 'b'},
        {'l': 'N', 'k': 'n'},
        {'l': 'M', 'k': 'm'},
        {'l': ':<br>;', 'k': ';', 's': ':'},
        {'l': '"<br>\'', 'k': '\'', 's': '"'},
        {'l': '\u2190', 'c': 'nav-key', 'k': '*MLt'},
        {'l': '\u203b', 'c': 'nav-key', 'k': '*Cn'},
        {'l': '\u2192', 'c': 'nav-key', 'k': '*MRt'},
        # Row 7 — Modifiers + Space + Blue zone bottom
        {'l': 'Caps<br>Lock', 'stack': True, 'k': '*CaLk'},
        {'l': 'Shift \u2191', 'span': 2, 'k': '*Shft'},
        {'l': 'SPACE', 'span': 3, 'k': ' '},
        {'l': '<<br>,', 'k': ',', 's': '<'},
        {'l': '><br>.', 'k': '.', 's': '>'},
        {'l': '?<br>/', 'k': '/', 's': '?'},
        {'l': '\u2199', 'c': 'nav-key', 'k': '*MDL'},
        {'l': '\u2193', 'c': 'nav-key', 'k': '*MDn'},
        {'l': '\u2198', 'c': 'nav-key', 'k': '*MDR'},
        # Row 8 — Bottom control + Blue zone footer
        {'l': 'Ctrl', 'k': '*Ctrl'},
        {'l': 'Alt Option', 'k': '*Alt'},
        {'l': '\u2318', 'k': '*Cmd'},
        {'l': '\u2190', 'k': '*Lft'},
        {'l': '\u2192', 'k': '*Rgt'},
        {'l': '\u2191', 'k': '*Up2'},
        {'l': '\u2193', 'k': '*Dn2'},
        {'l': 'Enter \u21b5', 'span': 2, 'k': '\r'},
        {'l': '\u203b\u203b', 'c': 'nav-key', 'k': '*Spkl'},
        {'l': '\u2b17 R', 'c': 'oval', 'k': '*LClk'},
        {'l': '\u2b16 Drag', 'c': 'oval', 'k': '*RClk'},
    ]


@pytest.fixture
def numpad_data():
    """numpadData from webpage.h:473-511, transcribed to Python tuples."""
    return [
        # Row 1 — Speed / Accel controls
        (1, 3, 1, 1, 'Spd\u2212', '*SpdD'),
        (1, 4, 1, 2, 'Speed: 5', '*SpdVal'),
        (1, 6, 1, 1, 'Spd+', '*SpdU'),
        (1, 7, 1, 1, 'Acl\u2212', '*AclD'),
        (1, 8, 1, 2, 'Accel: 0', '*AclVal'),
        (1, 10, 1, 1, 'Acl+', '*AclU'),
        # Row 2 — Exit
        (2, 5, 1, 4, '\u2715 Exit', '*NP'),
        # Row 3 — Media keys
        (3, 5, 1, 1, 'Mute', '*MEDmute'),   (3, 6, 1, 1, 'Vol\u2212', '*MEDvoldn'),
        (3, 7, 1, 1, 'Vol+', '*MEDvolup'),  (3, 8, 1, 1, 'Play', '*MEDplay'),
        # Row 4 — Media keys
        (4, 5, 1, 1, 'Prev', '*MEDprev'),   (4, 6, 1, 1, 'RW', '*MEDrw'),
        (4, 7, 1, 1, 'FF', '*MEDff'),   (4, 8, 1, 1, 'Next', '*MEDnext'),
        # Row 4 — Left keypad
        (4, 1, 1, 1, 'NL', '*NL'),    (4, 2, 1, 1, '/', '*NP/'),
        (4, 3, 1, 1, '*', '*NP*'),    (4, 4, 1, 1, '\u2212', '*NP-'),
        # Row 5 — Left
        (5, 1, 1, 1, '7<br>Home', '*NP7'),   (5, 2, 1, 1, '8<br>\u2191', '*NP8'),
        (5, 3, 1, 1, '9<br>PgUp', '*NP9'),   (5, 4, 2, 1, '+', '*NP+'),
        # Row 6 — Left
        (6, 1, 1, 1, '4<br>\u2190', '*NP4'),  (6, 2, 1, 1, '5', '*NP5'),
        (6, 3, 1, 1, '6<br>\u2192', '*NP6'),
        # Row 7 — Left
        (7, 1, 1, 1, '1<br>End', '*NP1'),    (7, 2, 1, 1, '2<br>\u2193', '*NP2'),
        (7, 3, 1, 1, '3<br>PgDn', '*NP3'),   (7, 4, 2, 1, 'Enter', '*NPEn'),
        # Row 8 — Left
        (8, 1, 1, 2, '0<br>Ins', '*NP0'),    (8, 3, 1, 1, '.<br>Del', '*NPD'),
        # Row 4 — Right keypad (mirror)
        (4, 9, 1, 1, 'NL', '*NL'),   (4, 10, 1, 1, '/', '*NP/'),
        (4, 11, 1, 1, '*', '*NP*'),  (4, 12, 1, 1, '\u2212', '*NP-'),
        # Row 5 — Right
        (5, 9, 1, 1, '7<br>Home', '*NP7'),   (5, 10, 1, 1, '8<br>\u2191', '*NP8'),
        (5, 11, 1, 1, '9<br>PgUp', '*NP9'),  (5, 12, 2, 1, '+', '*NP+'),
        # Row 6 — Right
        (6, 9, 1, 1, '4<br>\u2190', '*NP4'),  (6, 10, 1, 1, '5', '*NP5'),
        (6, 11, 1, 1, '6<br>\u2192', '*NP6'),
        # Row 7 — Right
        (7, 9, 1, 1, '1<br>End', '*NP1'),    (7, 10, 1, 1, '2<br>\u2193', '*NP2'),
        (7, 11, 1, 1, '3<br>PgDn', '*NP3'),  (7, 12, 2, 1, 'Enter', '*NPEn'),
        # Row 8 — Right
        (8, 9, 1, 2, '0<br>Ins', '*NP0'),    (8, 11, 1, 1, '.<br>Del', '*NPD'),
    ]


@pytest.fixture
def mod_keys():
    return {'*Shft': 'shift', '*Ctrl': 'ctrl', '*Alt': 'alt', '*Cmd': 'meta'}


@pytest.fixture
def media_keys():
    """Media key code to Consumer usage mapping."""
    return {
        '*MEDmute': 0x00E2,
        '*MEDvoldn': 0x00EA,
        '*MEDvolup': 0x00E9,
        '*MEDplay': 0x00CD,
        '*MEDnext': 0x00B5,
        '*MEDprev': 0x00B6,
        '*MEDff': 0x00B3,
        '*MEDrw': 0x00B4,
    }
