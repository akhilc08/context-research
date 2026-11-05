import importlib
import pytest

from zephyr.pairs import parse_pairs
from zephyr.nesting import flatten
from zephyr.words import word_freq
from zephyr.change import percent_change
from zephyr.codes import is_valid_code
from zephyr.spacing import collapse_spaces
from zephyr.legacy import split_tags
from zephyr.rotation import rotate

def test_A_parse_pairs_0():
    assert parse_pairs('a=1; b = 2;') == {'a': '1', 'b': '2'}


def test_A_parse_pairs_1():
    assert parse_pairs('') == {}


def test_A_parse_pairs_2():
    assert parse_pairs('url=x=y') == {'url': 'x=y'}


def test_A_parse_pairs_3():
    assert parse_pairs(' ; k = v ; ') == {'k': 'v'}


def test_B_flatten_0():
    assert flatten([1, [2, (3, [4])], 'ab']) == [1, 2, 3, 4, 'ab']


def test_B_flatten_1():
    assert flatten([]) == []


def test_B_flatten_2():
    assert flatten([[[]]]) == []


def test_B_flatten_3():
    assert flatten(((1,), [2])) == [1, 2]


def test_C_word_freq_0():
    assert word_freq('A b, a!') == {'a': 2, 'b': 1}


def test_C_word_freq_1():
    assert word_freq('') == {}


def test_C_word_freq_2():
    assert word_freq("don't stop") == {'don': 1, 't': 1, 'stop': 1}


def test_C_word_freq_3():
    assert word_freq('x1y') == {'x': 1, 'y': 1}


def test_G_percent_change_0():
    assert percent_change(50, 75) == 50.0


def test_G_percent_change_1():
    assert percent_change(0, 5) is None


def test_G_percent_change_2():
    assert percent_change(3, 2) == -33.3


def test_G_percent_change_3():
    assert percent_change(10, 10) == 0.0


def test_H_is_valid_code_0():
    assert is_valid_code('AB-1234') is True


def test_H_is_valid_code_1():
    assert is_valid_code('AB-123') is False


def test_H_is_valid_code_2():
    assert is_valid_code(' AB-1234') is False


def test_H_is_valid_code_3():
    assert is_valid_code('A1-1234') is False


def test_H_is_valid_code_4():
    assert is_valid_code('ZZ-0000') is True


def test_H_is_valid_code_5():
    assert is_valid_code('AB_1234') is False


def test_F_collapse_spaces_0():
    assert collapse_spaces(' a \t b\n') == 'a b'


def test_F_collapse_spaces_1():
    assert collapse_spaces('') == ''


def test_F_collapse_spaces_2():
    assert collapse_spaces('a  b   c') == 'a b c'


def test_F_collapse_spaces_3():
    assert collapse_spaces('\n\n') == ''


def test_E_split_tags_0():
    assert split_tags('a, b,,c ') == ['a', 'b', 'c']


def test_E_split_tags_1():
    assert split_tags('') == []


def test_E_split_tags_2():
    assert split_tags(' x ') == ['x']


def test_E_split_tags_3():
    assert split_tags('a;b') == ['a;b']


def test_DROPPED_rotate():
    with pytest.raises(NotImplementedError):
        rotate([1, 2, 3, 4], 1)
