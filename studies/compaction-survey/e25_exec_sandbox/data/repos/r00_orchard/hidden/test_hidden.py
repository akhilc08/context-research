import importlib
import pytest

from orchard.intervals import merge_intervals
from orchard.numbers import extract_numbers
from orchard.change import percent_change
from orchard.chunking import chunk
from orchard.spacing import collapse_spaces
from orchard.codes import is_valid_code
from orchard.legacy import lookup
from orchard.ranking import top_k

def test_A_merge_intervals_0():
    assert merge_intervals([(5, 6), (1, 3), (2, 4)]) == [(1, 4), (5, 6)]


def test_A_merge_intervals_1():
    assert merge_intervals([]) == []


def test_A_merge_intervals_2():
    assert merge_intervals([(1, 2), (2, 3)]) == [(1, 3)]


def test_A_merge_intervals_3():
    assert merge_intervals([(1, 10), (2, 3)]) == [(1, 10)]


def test_B_extract_numbers_0():
    assert extract_numbers('a12b3') == [12, 3]


def test_B_extract_numbers_1():
    assert extract_numbers('-4.50') == [4, 50]


def test_B_extract_numbers_2():
    assert extract_numbers('') == []


def test_B_extract_numbers_3():
    assert extract_numbers('007x') == [7]


def test_B_extract_numbers_4():
    assert extract_numbers('1 2 3') == [1, 2, 3]


def test_C_percent_change_0():
    assert percent_change(50, 75) == 50.0


def test_C_percent_change_1():
    assert percent_change(0, 5) is None


def test_C_percent_change_2():
    assert percent_change(3, 2) == -33.3


def test_C_percent_change_3():
    assert percent_change(10, 10) == 0.0


def test_G_chunk_0():
    assert chunk([1, 2, 3], 2) == [[1, 2], [3]]


def test_G_chunk_1():
    assert chunk([], 3) == []


def test_G_chunk_2():
    assert chunk([1, 2], 5) == [[1, 2]]


def test_G_chunk_3():
    with pytest.raises(ValueError):
        chunk([1], 0)


def test_H_collapse_spaces_0():
    assert collapse_spaces(' a \t b\n') == 'a b'


def test_H_collapse_spaces_1():
    assert collapse_spaces('') == ''


def test_H_collapse_spaces_2():
    assert collapse_spaces('a  b   c') == 'a b c'


def test_H_collapse_spaces_3():
    assert collapse_spaces('\n\n') == ''


def test_F_is_valid_code_0():
    assert is_valid_code('AB-1234') is True


def test_F_is_valid_code_1():
    assert is_valid_code('AB-123') is False


def test_F_is_valid_code_2():
    assert is_valid_code(' AB-1234') is False


def test_F_is_valid_code_3():
    assert is_valid_code('A1-1234') is False


def test_F_is_valid_code_4():
    assert is_valid_code('ZZ-0000') is True


def test_F_is_valid_code_5():
    assert is_valid_code('AB_1234') is False


def test_E_lookup_0():
    assert lookup({'Alpha': 1}, ' alpha ') == 1


def test_E_lookup_1():
    assert lookup({'b': 2}, 'B') == 2


def test_E_lookup_2():
    assert lookup({}, 'x', 0) == 0


def test_E_lookup_3():
    assert lookup({'a': 1}, 'b') is None


def test_DROPPED_top_k():
    with pytest.raises(NotImplementedError):
        top_k({'a': 1, 'b': 3, 'c': 3}, 2)
