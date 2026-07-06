"""Test gridData structure: completeness, field requirements, key codes."""
import pytest


GRID_COLS = 12
GRID_ROWS = 8


class TestStructure:
    def test_correct_number_of_cells(self, grid_data):
        assert len(grid_data) == 91

    def test_every_cell_has_k_property(self, grid_data):
        for i, cell in enumerate(grid_data):
            assert 'k' in cell, f"Cell {i} missing 'k' property: {cell}"

    def test_k_is_non_empty_string(self, grid_data):
        for i, cell in enumerate(grid_data):
            assert isinstance(cell['k'], str) and len(cell['k']) > 0, (
                f"Cell {i} has invalid k={cell['k']!r}"
            )

    def test_every_cell_has_l_label(self, grid_data):
        for i, cell in enumerate(grid_data):
            assert 'l' in cell, f"Cell {i} missing 'l' label: {cell}"


class TestFunctionKeys:
    def test_twelve_f_keys_present(self, grid_data):
        f_keys = [c for c in grid_data if c['k'].startswith('*F')]
        assert len(f_keys) == 12

    def test_all_f_keys_have_f_key_class(self, grid_data):
        f_keys = [c for c in grid_data if c['k'].startswith('*F')]
        for cell in f_keys:
            assert cell.get('c') == 'f-key', f"{cell['k']} missing f-key class"

    def test_f_key_codes_sequential(self, grid_data):
        f_keys = [c for c in grid_data if c['k'].startswith('*F')]
        for i, cell in enumerate(f_keys):
            assert cell['k'] == f'*F{i + 1}', f"Expected *F{i+1}, got {cell['k']}"


class TestNumberSymbolPairs:
    def test_all_number_symbols_have_shift_property(self, grid_data):
        digits = [c for c in grid_data if c['k'] in '0123456789']
        for cell in digits:
            assert 's' in cell, f"Digit {cell['k']} missing shift symbol"

    def test_number_symbol_pairs_correct(self, grid_data):
        pairs = {'1': '!', '2': '@', '3': '#', '4': '$', '5': '%',
                 '6': '^', '7': '&', '8': '*', '9': '(', '0': ')'}
        for cell in grid_data:
            if cell['k'] in pairs:
                assert cell['s'] == pairs[cell['k']], (
                    f"Shift symbol for {cell['k']} should be {pairs[cell['k']]!r}, got {cell.get('s')!r}"
                )
                assert cell['l'] == f"{pairs[cell['k']]}<br>{cell['k']}"


class TestModifierKeys:
    def test_modifiers_present(self, grid_data):
        mod_keys = ['*Shft', '*Ctrl', '*Alt', '*Cmd', '*CaLk']
        found = {c['k'] for c in grid_data}
        for mk in mod_keys:
            assert mk in found, f"Modifier {mk} missing from grid"

    def test_caps_lock_has_stack_layout(self, grid_data):
        cal = [c for c in grid_data if c['k'] == '*CaLk']
        assert len(cal) == 1
        assert cal[0].get('stack') is True


class TestNavigationZone:
    NAV_KEYS = {'*MUL', '*MUp', '*MUR', '*MLt', '*Cn', '*MRt',
                '*MDL', '*MDn', '*MDR', '*Spkl'}

    def test_all_nav_keys_have_nav_class(self, grid_data):
        for cell in grid_data:
            if cell['k'] in self.NAV_KEYS:
                assert cell.get('c') == 'nav-key', (
                    f"Nav key {cell['k']} missing nav-key class"
                )

    def test_nav_key_count(self, grid_data):
        nav = [c for c in grid_data if c.get('c') == 'nav-key']
        assert len(nav) == len(self.NAV_KEYS)

    def test_mouse_click_keys_have_oval_class(self, grid_data):
        oval = [c for c in grid_data if c.get('c') == 'oval']
        k = {c['k'] for c in oval}
        assert '*LClk' in k
        assert '*RClk' in k


class TestSpanBounds:
    def test_no_span_exceeds_grid(self, grid_data):
        for cell in grid_data:
            span = cell.get('span', 1)
            assert 1 <= span <= 3, f"Span {span} out of range for {cell['k']}"

    def test_span_2_keys(self, grid_data):
        span2 = [c for c in grid_data if c.get('span') == 2]
        assert len(span2) >= 2


class TestSpecialKeys:
    @pytest.mark.parametrize("key_code,label_fragment", [
        ('*SmT', 'Smart'),
        ('*Mac', 'Mac Mode'),
        ('*NP', 'Num Pad'),
        ('*Ins', 'Insert'),
        ('*Home', 'Home'),
        ('*End', 'End'),
        ('*PgUp', 'PgUp'),
        ('*PgDn', 'PgDn'),
        ('*Del', 'Del'),
        ('\x1b', 'Esc'),
        ('\t', 'Tab'),
        ('\b', 'Backspace'),
        ('\r', 'Enter'),
    ])
    def test_special_keys_present(self, grid_data, key_code, label_fragment):
        found = [c for c in grid_data if c['k'] == key_code]
        assert len(found) >= 1, f"Key {key_code!r} ({label_fragment}) not found"

    def test_tab_has_shift_symbol(self, grid_data):
        tab = [c for c in grid_data if c['k'] == '\t']
        assert len(tab) == 1
        assert tab[0].get('s') == '*SHT'


class TestNoDuplicateGridPositions:
    def test_unique_k_values_for_single_instance_keys(self, grid_data):
        k_counts = {}
        for cell in grid_data:
            k = cell['k']
            k_counts[k] = k_counts.get(k, 0) + 1
        dups = {k: v for k, v in k_counts.items() if v > 1}
        assert len(dups) == 0, f"Duplicate k values found: {dups}"
