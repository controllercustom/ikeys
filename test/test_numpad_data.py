"""Test numpadData structure: field validity, left/right symmetry, key codes."""
import pytest


GRID_COLS = 12
GRID_ROWS = 8

# Numpad entry: (row, col, rowSpan, colSpan, label, keyCode)
ENTRY_LEN = 6
ROW_IDX = 0
COL_IDX = 1
ROWSPAN_IDX = 2
COLSPAN_IDX = 3
LABEL_IDX = 4
CODE_IDX = 5


class TestStructure:
    def test_every_entry_has_six_fields(self, numpad_data):
        for i, entry in enumerate(numpad_data):
            assert len(entry) == ENTRY_LEN, (
                f"Entry {i} has {len(entry)} fields, expected {ENTRY_LEN}: {entry}"
            )

    def test_every_entry_has_key_code(self, numpad_data):
        for i, entry in enumerate(numpad_data):
            code = entry[CODE_IDX]
            assert isinstance(code, str) and len(code) > 0, (
                f"Entry {i} has empty or invalid key code: {entry}"
            )


class TestCoordinates:
    @pytest.mark.parametrize("idx_name", [ROW_IDX, COL_IDX])
    def test_row_and_col_positive(self, numpad_data, idx_name):
        names = {ROW_IDX: 'row', COL_IDX: 'col'}
        for i, entry in enumerate(numpad_data):
            val = entry[idx_name]
            assert isinstance(val, int) and val >= 1, (
                f"Entry {i} {names[idx_name]}={val} must be >= 1"
            )

    def test_row_in_range(self, numpad_data):
        for i, entry in enumerate(numpad_data):
            r = entry[ROW_IDX]
            assert 1 <= r <= GRID_ROWS, (
                f"Entry {i} row={r} out of range [1, {GRID_ROWS}]"
            )

    def test_col_in_range(self, numpad_data):
        for i, entry in enumerate(numpad_data):
            c = entry[COL_IDX]
            assert 1 <= c <= GRID_COLS, (
                f"Entry {i} col={c} out of range [1, {GRID_COLS}]"
            )


class TestSpans:
    def test_row_span_positive(self, numpad_data):
        for i, entry in enumerate(numpad_data):
            rs = entry[ROWSPAN_IDX]
            assert isinstance(rs, int) and rs >= 1, (
                f"Entry {i} rowSpan={rs} must be >= 1"
            )

    def test_col_span_positive(self, numpad_data):
        for i, entry in enumerate(numpad_data):
            cs = entry[COLSPAN_IDX]
            assert isinstance(cs, int) and cs >= 1, (
                f"Entry {i} colSpan={cs} must be >= 1"
            )

    def test_span_does_not_exceed_grid(self, numpad_data):
        for i, entry in enumerate(numpad_data):
            r, c, rs, cs = entry[ROW_IDX], entry[COL_IDX], entry[ROWSPAN_IDX], entry[COLSPAN_IDX]
            assert r + rs - 1 <= GRID_ROWS, (
                f"Entry {i} row+rowSpan exceeds grid: row={r}, span={rs}"
            )
            assert c + cs - 1 <= GRID_COLS, (
                f"Entry {i} col+colSpan exceeds grid: col={c}, span={cs}"
            )


class TestKeyCodes:
    def test_all_key_codes_start_with_star(self, numpad_data):
        for i, entry in enumerate(numpad_data):
            code = entry[CODE_IDX]
            assert code.startswith('*'), (
                f"Entry {i} code {code!r} must start with '*'"
            )

    def test_numpad_keys_have_np_prefix(self, numpad_data):
        for i, entry in enumerate(numpad_data):
            code = entry[CODE_IDX]
            if code != '*NL' and code != '*NP' and code != '*SpdD' \
                    and code != '*SpdU' and code != '*SpdVal' \
                    and code != '*AclD' and code != '*AclU' and code != '*AclVal' \
                    and not code.startswith('*MED'):
                assert code.startswith('*NP'), (
                    f"Entry {i} code {code!r} should start with '*NP'"
                )

    def test_mouse_config_keys_have_correct_prefixes(self, numpad_data):
        config_keys = {e[CODE_IDX] for e in numpad_data
                       if e[CODE_IDX] in ('*SpdD', '*SpdU', '*SpdVal',
                                          '*AclD', '*AclU', '*AclVal')}
        assert len(config_keys) == 6


class TestLeftRightSymmetry:
    def get_keypad_only(self, entries):
        """Filter to dual-keypad rows only (4-8), excluding config controls."""
        return sorted(
            [e for e in entries if 4 <= e[ROW_IDX] <= 8],
            key=lambda e: (e[ROW_IDX], e[COL_IDX])
        )

    def get_entries_by_col(self, entries, col_range):
        return sorted(
            [e for e in entries if col_range[0] <= e[COL_IDX] <= col_range[1]],
            key=lambda e: (e[ROW_IDX], e[COL_IDX])
        )

    def test_left_and_right_keypads_have_same_count(self, numpad_data):
        rows = self.get_keypad_only(numpad_data)
        left = self.get_entries_by_col(rows, (1, 4))
        right = self.get_entries_by_col(rows, (9, 12))
        assert len(left) == len(right), (
            f"Left keypad ({len(left)} entries) != Right keypad ({len(right)} entries)"
        )

    def test_left_right_entries_correspond_by_row(self, numpad_data):
        rows = self.get_keypad_only(numpad_data)
        left = self.get_entries_by_col(rows, (1, 4))
        right = self.get_entries_by_col(rows, (9, 12))
        for l_entry, r_entry in zip(left, right):
            assert l_entry[ROW_IDX] == r_entry[ROW_IDX], (
                f"Row mismatch: left row={l_entry[ROW_IDX]} vs right row={r_entry[ROW_IDX]}"
            )
            assert l_entry[ROWSPAN_IDX] == r_entry[ROWSPAN_IDX]
            assert l_entry[COLSPAN_IDX] == r_entry[COLSPAN_IDX]
            assert l_entry[CODE_IDX] == r_entry[CODE_IDX], (
                f"Code mismatch: left={l_entry[CODE_IDX]} vs right={r_entry[CODE_IDX]} "
                f"at row {l_entry[ROW_IDX]}"
            )

    def test_exit_button_centered(self, numpad_data):
        exit_btns = [e for e in numpad_data if e[CODE_IDX] == '*NP']
        assert len(exit_btns) == 1
        assert exit_btns[0][ROW_IDX] == 2
        assert exit_btns[0][COL_IDX] == 5
        assert exit_btns[0][COLSPAN_IDX] == 4
