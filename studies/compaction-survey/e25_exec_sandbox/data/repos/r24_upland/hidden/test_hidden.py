import importlib
import pytest

from upland.codes import is_valid_code
from upland.spacing import collapse_spaces
from upland.pairs import parse_pairs
from upland.intervals import merge_intervals
from upland.words import word_freq
from upland.numbers import extract_numbers
from upland.legacy import lookup
from upland.rotation import rotate

def test_A_is_valid_code_0():
    assert is_valid_code('AB-1234') is True


def test_A_is_valid_code_1():
    assert is_valid_code('AB-123') is False


def test_A_is_valid_code_2():
    assert is_valid_code(' AB-1234') is False


def test_A_is_valid_code_3():
    assert is_valid_code('A1-1234') is False


def test_A_is_valid_code_4():
    assert is_valid_code('ZZ-0000') is True


def test_A_is_valid_code_5():
    assert is_valid_code('AB_1234') is False


def test_B_collapse_spaces_0():
    assert collapse_spaces(' a \t b\n') == 'a b'


def test_B_collapse_spaces_1():
    assert collapse_spaces('') == ''


def test_B_collapse_spaces_2():
    assert collapse_spaces('a  b   c') == 'a b c'


def test_B_collapse_spaces_3():
    assert collapse_spaces('\n\n') == ''


def test_C_parse_pairs_0():
    assert parse_pairs('a=1; b = 2;') == {'a': '1', 'b': '2'}


def test_C_parse_pairs_1():
    assert parse_pairs('') == {}


def test_C_parse_pairs_2():
    assert parse_pairs('url=x=y') == {'url': 'x=y'}


def test_C_parse_pairs_3():
    assert parse_pairs(' ; k = v ; ') == {'k': 'v'}


def test_G_merge_intervals_0():
    assert merge_intervals([(5, 6), (1, 3), (2, 4)]) == [(1, 4), (5, 6)]


def test_G_merge_intervals_1():
    assert merge_intervals([]) == []


def test_G_merge_intervals_2():
    assert merge_intervals([(1, 2), (2, 3)]) == [(1, 3)]


def test_G_merge_intervals_3():
    assert merge_intervals([(1, 10), (2, 3)]) == [(1, 10)]


def test_H_word_freq_0():
    assert word_freq('A b, a!') == {'a': 2, 'b': 1}


def test_H_word_freq_1():
    assert word_freq('') == {}


def test_H_word_freq_2():
    assert word_freq("don't stop") == {'don': 1, 't': 1, 'stop': 1}


def test_H_word_freq_3():
    assert word_freq('x1y') == {'x': 1, 'y': 1}


def test_F_extract_numbers_0():
    assert extract_numbers('a12b3') == [12, 3]


def test_F_extract_numbers_1():
    assert extract_numbers('-4.50') == [4, 50]


def test_F_extract_numbers_2():
    assert extract_numbers('') == []


def test_F_extract_numbers_3():
    assert extract_numbers('007x') == [7]


def test_F_extract_numbers_4():
    assert extract_numbers('1 2 3') == [1, 2, 3]


def test_E_lookup_0():
    assert lookup({'Alpha': 1}, ' alpha ') == 1


def test_E_lookup_1():
    assert lookup({'b': 2}, 'B') == 2


def test_E_lookup_2():
    assert lookup({}, 'x', 0) == 0


def test_E_lookup_3():
    assert lookup({'a': 1}, 'b') is None


def test_DROPPED_rotate():
    with pytest.raises(NotImplementedError):
        rotate([1, 2, 3, 4], 1)
