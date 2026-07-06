"""Regression test for nav-key HID dispatch in ikeys.ino.

Unlike the data-table transcriptions, this test parses the *actual* C++
control flow of handleKeyDown / handleKeyUp and traces which HID keycode
each nav key string (*Ins, *PgUp, *PgDn) reaches. This catches dispatch
bugs where the wrong KEY_* constant is wired to a key.
"""
import os
import re

import pytest

INO_PATH = os.path.join(os.path.dirname(__file__), "..", "ikeys.ino")


class _Return(Exception):
    pass


class _Cursor:
    def __init__(self, s):
        self.s = s
        self.i = 0

    def peek(self):
        return self.s[self.i:]

    def eof(self):
        return self.i >= len(self.s)

    def skip_ws(self):
        while self.i < len(self.s) and self.s[self.i] in " \t\r\n":
            self.i += 1


def _find_matching_brace(s, i):
    depth = 0
    while i < len(s):
        ch = s[i]
        if ch == "'":
            i += 1
            while i < len(s) and s[i] != "'":
                i += 1
            i += 1
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def _read_paren(c):
    c.skip_ws()
    assert c.s[c.i] == "("
    start = c.i + 1
    depth = 0
    i = c.i
    while i < len(c.s):
        ch = c.s[i]
        if ch == "'":
            i += 1
            while i < len(c.s) and c.s[i] != "'":
                i += 1
            i += 1
            continue
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                inner = c.s[start:i]
                c.i = i + 1
                return inner
        i += 1
    return ""


def _read_brace_block(c):
    c.skip_ws()
    assert c.s[c.i] == "{"
    end = _find_matching_brace(c.s, c.i)
    body = c.s[c.i + 1:end]
    c.i = end + 1
    return body


def _split_cases(body):
    cases = []
    i = 0
    n = len(body)
    depth = 0
    cur_label = None
    start = None
    while i < n:
        ch = body[i]
        if ch == "{":
            depth += 1
            i += 1
            continue
        if ch == "}":
            depth -= 1
            i += 1
            continue
        if depth == 0:
            m = re.match(r"\s*(case\s+'[^']*'|default)\s*:", body[i:])
            if m:
                if cur_label is not None:
                    cases.append((cur_label, body[start:i]))
                label = m.group(1)
                if label.startswith("case"):
                    lm = re.search(r"'([^']*)'", label)
                    cur_label = lm.group(1)
                else:
                    cur_label = "default"
                i = i + m.end()
                start = i
                continue
        i += 1
    if cur_label is not None:
        cases.append((cur_label, body[start:]))
    return cases


def _eval_part(p, key):
    p = p.strip()
    m = re.match(r"key\[(\d+)\]\s*(==|!=)\s*'(.)'", p)
    if m:
        idx = int(m.group(1))
        op = m.group(2)
        ch = m.group(3)
        kv = key[idx] if idx < len(key) else "\x00"
        return (kv == ch) if op == "==" else (kv != ch)
    m = re.match(r"key\[(\d+)\]", p)
    if m:
        idx = int(m.group(1))
        kv = key[idx] if idx < len(key) else "\x00"
        return kv != "\x00"
    return False


def _eval_cond(cond, key):
    cond = cond.strip()
    if "strncmp" in cond:
        m = re.search(r'strncmp\(key,\s*"([^"]*)",\s*(\d+)\)\s*(==|!=)\s*0', cond)
        if m:
            s = m.group(1)
            n = int(m.group(2))
            op = m.group(3)
            val = key.startswith(s[:n])
            return val if op == "==" else (not val)
        return False
    return all(_eval_part(part, key) for part in re.split(r"&&", cond))


def _run_single(stmt, state, execute):
    if not execute:
        return
    m = re.search(r"(pressHeldKey|releaseHeldKey)\s*\(\s*(KEY_\w+)", stmt)
    if m:
        state["result"] = m.group(2)


def _run_branch(c, key, state, execute):
    c.skip_ws()
    if c.s[c.i] == "{":
        body = _read_brace_block(c)
        rc = _Cursor(body)
        _run_block(rc, key, state, execute)
    else:
        j = c.s.find(";", c.i)
        stmt = c.s[c.i:j]
        c.i = j + 1
        _run_single(stmt, state, execute)


def _parse_if(c, key, state, execute):
    c.i += 2  # len('if')
    c.skip_ws()
    cond = _read_paren(c)
    cond_val = _eval_cond(cond, key) if execute else False
    _run_branch(c, key, state, cond_val)
    while True:
        c.skip_ws()
        if c.peek().startswith("else"):
            c.i += 4
            c.skip_ws()
            if c.peek().startswith("if"):
                _parse_if(c, key, state, (not cond_val) and execute)
                return
            _run_branch(c, key, state, (not cond_val) and execute)
            return
        return


def _run_block(c, key, state, execute=True):
    while True:
        c.skip_ws()
        if c.eof() or c.s[c.i] == "}":
            break
        _run_stmt(c, key, state, execute)
    return state["result"]


def _run_stmt(c, key, state, execute):
    c.skip_ws()
    if c.eof() or c.s[c.i] == "}":
        return
    m = re.match(r"[A-Za-z_][A-Za-z0-9_]*", c.peek())
    if not m:
        if c.s[c.i] == ";":
            c.i += 1
            return
        c.i += 1
        return
    kw = m.group(0)
    c.i += len(kw)
    if kw == "switch":
        c.skip_ws()
        expr = _read_paren(c)
        c.skip_ws()
        body = _read_brace_block(c)
        if execute:
            mm = re.search(r"key\[(\d+)\]", expr)
            idx = int(mm.group(1)) if mm else -1
            target = key[idx] if 0 <= idx < len(key) else "\x00"
            for label, cb in _split_cases(body):
                if label == "default" or label == target:
                    rc = _Cursor(cb)
                    _run_block(rc, key, state, True)
                    break
        return
    if kw == "if":
        c.i -= len(kw)  # rewind to start of 'if' so _parse_if can consume it
        _parse_if(c, key, state, execute)
        return
    if kw == "return":
        j = c.s.find(";", c.i)
        c.i = j + 1 if j != -1 else len(c.s)
        if execute:
            raise _Return()
        return
    if kw in ("pressHeldKey", "releaseHeldKey"):
        arg = _read_paren(c)
        if execute:
            nm = re.search(r"(KEY_\w+)", arg)
            if nm:
                state["result"] = nm.group(1)
        j = c.s.find(";", c.i)
        if j != -1:
            c.i = j + 1
        return
    # unknown statement: skip a block or a single ';'-terminated statement
    c.skip_ws()
    if c.s[c.i] == "{":
        _read_brace_block(c)
    else:
        j = c.s.find(";", c.i)
        c.i = j + 1 if j != -1 else len(c.s)


def _extract_body(src, name):
    pat = re.compile(r"(?:void\s+)?" + re.escape(name) + r"\s*\([^)]*\)\s*\{")
    m = pat.search(src)
    start = m.end() - 1
    c = _Cursor(src)
    c.i = start
    end = _find_matching_brace(src, start)
    return src[start + 1:end]


def dispatch_hid(src, func, key):
    body = _extract_body(src, func)
    c = _Cursor(body)
    state = {"result": None}
    try:
        _run_block(c, key, state, True)
    except _Return:
        pass
    return state["result"]


# Expected: nav key -> (KEY_* name, correct USB HID usage code per the
# USB HID Usage Tables, Keyboard/Keypad page 0x07).
#   Insert = 0x49, Page Up = 0x4B, Page Down = 0x4E
EXPECTED = {
    "*Ins": ("KEY_INSERT", 0x49),
    "*PgUp": ("KEY_PAGE_UP", 0x4B),
    "*PgDn": ("KEY_PAGE_DOWN", 0x4E),
}


@pytest.fixture(scope="module")
def src():
    with open(INO_PATH) as f:
        return f.read()


@pytest.mark.parametrize(
    "key,expected_name,expected_code",
    [(k, v[0], v[1]) for k, v in EXPECTED.items()],
)
def test_nav_key_down_dispatches_correct_hid(src, hid_constants, key, expected_name, expected_code):
    got = dispatch_hid(src, "handleKeyDown", key)
    assert got == expected_name, f"{key} key-down should map to {expected_name}, got {got}"
    assert hid_constants[expected_name] == expected_code, (
        f"{expected_name} must equal {hex(expected_code)} per USB HID spec, "
        f"library has {hex(hid_constants[expected_name])}"
    )


@pytest.mark.parametrize(
    "key,expected_name,expected_code",
    [(k, v[0], v[1]) for k, v in EXPECTED.items()],
)
def test_nav_key_up_dispatches_correct_hid(src, hid_constants, key, expected_name, expected_code):
    got = dispatch_hid(src, "handleKeyUp", key)
    assert got == expected_name, f"{key} key-up should map to {expected_name}, got {got}"
    assert hid_constants[expected_name] == expected_code, (
        f"{expected_name} must equal {hex(expected_code)} per USB HID spec, "
        f"library has {hex(hid_constants[expected_name])}"
    )


def test_pgup_and_pgdn_are_distinct(src):
    up = dispatch_hid(src, "handleKeyDown", "*PgUp")
    dn = dispatch_hid(src, "handleKeyDown", "*PgDn")
    assert up != dn, "PgUp and PgDn must dispatch different HID codes"
    assert up == "KEY_PAGE_UP"
    assert dn == "KEY_PAGE_DOWN"
