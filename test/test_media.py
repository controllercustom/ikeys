"""Test media key data: code→usage mapping, numpad placement, completeness."""
import pytest

COL_IDX = 1
ROW_IDX = 0
CODE_IDX = 5


class TestMediaFixtures:
    def test_all_media_codes_have_valid_usages(self, media_keys):
        for code, usage in media_keys.items():
            assert isinstance(code, str) and code.startswith('*MED'), f"Bad code: {code!r}"
            assert isinstance(usage, int) and 0 < usage <= 0xFFFF, (
                f"{code} usage 0x{usage:04X} out of Consumer range"
            )

    def test_all_media_codes_appear_in_numpad_data(self, numpad_data, media_keys):
        codes_in_numpad = {e[CODE_IDX] for e in numpad_data}
        for code in media_keys:
            assert code in codes_in_numpad, f"Media key {code} missing from numpadData"

    def test_no_extra_media_keys_in_numpad(self, numpad_data, media_keys):
        numpad_media = {e[CODE_IDX] for e in numpad_data if e[CODE_IDX].startswith('*MED')}
        assert numpad_media == set(media_keys.keys()), (
            f"Extra *MED codes in numpadData not in media_keys: {numpad_media - set(media_keys.keys())}"
        )


class TestMediaPlacement:
    def test_media_keys_in_middle_columns(self, numpad_data):
        media_entries = [e for e in numpad_data if e[CODE_IDX].startswith('*MED')]
        assert len(media_entries) > 0
        for entry in media_entries:
            col = entry[COL_IDX]
            assert 5 <= col <= 8, (
                f"Media key {entry[CODE_IDX]} at col {col}, expected cols 5–8"
            )

    def test_media_keys_in_valid_rows(self, numpad_data):
        media_entries = [e for e in numpad_data if e[CODE_IDX].startswith('*MED')]
        for entry in media_entries:
            row = entry[ROW_IDX]
            assert 3 <= row <= 5, (
                f"Media key {entry[CODE_IDX]} at row {row}, expected rows 3–5"
            )

    def test_media_keys_have_single_span(self, numpad_data):
        media_entries = [e for e in numpad_data if e[CODE_IDX].startswith('*MED')]
        for entry in media_entries:
            assert entry[2] == 1, f"Media key {entry[CODE_IDX]} has rowSpan {entry[2]}, expected 1"
            assert entry[3] == 1, f"Media key {entry[CODE_IDX]} has colSpan {entry[3]}, expected 1"
