import importlib
import pytest

from osprey.pairs import parse_pairs
from osprey.stats import moving_average
from osprey.rotation import rotate
from osprey.intervals import merge_intervals
from osprey.numbers import extract_numbers
from osprey.codes import is_valid_code
from osprey.legacy import lookup
from osprey.unique import dedupe

def test_A_parse_pairs_0():
    assert parse_pairs('a=1; b = 2;') == {'a': '1', 'b': '2'}


def test_A_parse_pairs_1():
    assert parse_pairs('') == {}


def test_A_parse_pairs_2():
    assert parse_pairs('url=x=y') == {'url': 'x=y'}


def test_A_parse_pairs_3():
    assert parse_pairs(' ; k = v ; ') == {'k': 'v'}


def test_B_moving_average_0():
    assert moving_average([1, 2, 3, 4], 2) == [1.5, 2.5, 3.5]


def test_B_moving_average_1():
    assert moving_average([1], 3) == []


def test_B_moving_average_2():
    assert moving_average([1, 2, 2], 3) == [1.67]


def test_B_moving_average_3():
    with pytest.raises(ValueError):
        moving_average([1, 2], 0)


def test_C_rotate_0():
    assert rotate([1, 2, 3, 4], 1) == [4, 1, 2, 3]


def test_C_rotate_1():
    assert rotate([], 3) == []


def test_C_rotate_2():
    assert rotate([1, 2, 3], 4) == [3, 1, 2]


def test_C_rotate_3():
    assert rotate([1, 2, 3], -1) == [2, 3, 1]


def test_G_merge_intervals_0():
    assert merge_intervals([(5, 6), (1, 3), (2, 4)]) == [(1, 4), (5, 6)]


def test_G_merge_intervals_1():
    assert merge_intervals([]) == []


def test_G_merge_intervals_2():
    assert merge_intervals([(1, 2), (2, 3)]) == [(1, 3)]


def test_G_merge_intervals_3():
    assert merge_intervals([(1, 10), (2, 3)]) == [(1, 10)]


def test_H_extract_numbers_0():
    assert extract_numbers('a12b3') == [12, 3]


def test_H_extract_numbers_1():
    assert extract_numbers('-4.50') == [4, 50]


def test_H_extract_numbers_2():
    assert extract_numbers('') == []


def test_H_extract_numbers_3():
    assert extract_numbers('007x') == [7]


def test_H_extract_numbers_4():
    assert extract_numbers('1 2 3') == [1, 2, 3]


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


def test_DROPPED_dedupe():
    with pytest.raises(NotImplementedError):
        dedupe([3, 1, 3, 2, 1])
