"""Translate iKeys WebSocket key strings into Linux evdev codes.

The ESP32-S3 board enumerates on the host as a USB HID device; the kernel
translates HID usages (USB HID Usage Tables, keyboard/keypad page 0x07)
into Linux input-event codes. This module provides the translation so
end-to-end tests can assert the exact evdev key event a given iKeys key
is supposed to produce.
"""
from evdev import ecodes


# Single-character iKeys keys -> expected evdev KEY code (no shift held).
SINGLE_CHAR_TO_EVDEV = {
    'a': ecodes.KEY_A, 'b': ecodes.KEY_B, 'c': ecodes.KEY_C, 'd': ecodes.KEY_D,
    'e': ecodes.KEY_E, 'f': ecodes.KEY_F, 'g': ecodes.KEY_G, 'h': ecodes.KEY_H,
    'i': ecodes.KEY_I, 'j': ecodes.KEY_J, 'k': ecodes.KEY_K, 'l': ecodes.KEY_L,
    'm': ecodes.KEY_M, 'n': ecodes.KEY_N, 'o': ecodes.KEY_O, 'p': ecodes.KEY_P,
    'q': ecodes.KEY_Q, 'r': ecodes.KEY_R, 's': ecodes.KEY_S, 't': ecodes.KEY_T,
    'u': ecodes.KEY_U, 'v': ecodes.KEY_V, 'w': ecodes.KEY_W, 'x': ecodes.KEY_X,
    'y': ecodes.KEY_Y, 'z': ecodes.KEY_Z,
    '1': ecodes.KEY_1, '2': ecodes.KEY_2, '3': ecodes.KEY_3, '4': ecodes.KEY_4,
    '5': ecodes.KEY_5, '6': ecodes.KEY_6, '7': ecodes.KEY_7, '8': ecodes.KEY_8,
    '9': ecodes.KEY_9, '0': ecodes.KEY_0,
    ' ': ecodes.KEY_SPACE, '\r': ecodes.KEY_ENTER, '\b': ecodes.KEY_BACKSPACE,
    '\t': ecodes.KEY_TAB, '\x1b': ecodes.KEY_ESC,
    '`': ecodes.KEY_GRAVE, '-': ecodes.KEY_MINUS, '=': ecodes.KEY_EQUAL,
    '[': ecodes.KEY_LEFTBRACE, ']': ecodes.KEY_RIGHTBRACE, '\\': ecodes.KEY_BACKSLASH,
    ';': ecodes.KEY_SEMICOLON, '\'': ecodes.KEY_APOSTROPHE,
    ',': ecodes.KEY_COMMA, '.': ecodes.KEY_DOT, '/': ecodes.KEY_SLASH,
}


# Named (star-prefixed) iKeys keys -> expected evdev KEY code.
# Note: the firmware's arrow keys require the 4-char form (*Up2/*Dn2); a bare
# *Up/*Dn is intentionally not handled by ikeys.ino.
NAMED_KEY_TO_EVDEV = {
    '*Shft': ecodes.KEY_LEFTSHIFT, '*Ctrl': ecodes.KEY_LEFTCTRL,
    '*Alt': ecodes.KEY_LEFTALT, '*Cmd': ecodes.KEY_LEFTMETA,
    '*Home': ecodes.KEY_HOME, '*End': ecodes.KEY_END,
    '*Ins': ecodes.KEY_INSERT, '*Del': ecodes.KEY_DELETE,
    '*PgUp': ecodes.KEY_PAGEUP, '*PgDn': ecodes.KEY_PAGEDOWN,
    '*Lft': ecodes.KEY_LEFT, '*Rgt': ecodes.KEY_RIGHT,
    '*Up2': ecodes.KEY_UP, '*Dn2': ecodes.KEY_DOWN,
    '*CaLk': ecodes.KEY_CAPSLOCK, '*NL': ecodes.KEY_NUMLOCK,
    '*F1': ecodes.KEY_F1, '*F2': ecodes.KEY_F2, '*F3': ecodes.KEY_F3,
    '*F4': ecodes.KEY_F4, '*F5': ecodes.KEY_F5, '*F6': ecodes.KEY_F6,
    '*F7': ecodes.KEY_F7, '*F8': ecodes.KEY_F8, '*F9': ecodes.KEY_F9,
    '*F10': ecodes.KEY_F10, '*F11': ecodes.KEY_F11, '*F12': ecodes.KEY_F12,
    '*NP0': ecodes.KEY_KP0, '*NP1': ecodes.KEY_KP1, '*NP2': ecodes.KEY_KP2,
    '*NP3': ecodes.KEY_KP3, '*NP4': ecodes.KEY_KP4, '*NP5': ecodes.KEY_KP5,
    '*NP6': ecodes.KEY_KP6, '*NP7': ecodes.KEY_KP7, '*NP8': ecodes.KEY_KP8,
    '*NP9': ecodes.KEY_KP9, '*NP/': ecodes.KEY_KPSLASH, '*NP*': ecodes.KEY_KPASTERISK,
    '*NP-': ecodes.KEY_KPMINUS, '*NP+': ecodes.KEY_KPPLUS,
    '*NPEn': ecodes.KEY_KPENTER, '*NPD': ecodes.KEY_KPDOT,
}
