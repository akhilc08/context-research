import importlib
import pytest

from sable.pairs import parse_pairs
from sable.change import percent_change
from sable.spacing import collapse_spaces
from sable.ranking import top_k
from sable.codes import is_valid_code
from sable.words import word_freq
from sable.legacy import split_tags
from sable.slug import slugify

def test_A_parse_pairs_0():
    assert parse_pairs('a=1; b = 2;') == {'a': '1', 'b': '2'}


def test_A_parse_pairs_1():
    assert parse_pairs('') == {}


def test_A_parse_pairs_2():
    assert parse_pairs('url=x=y') == {'url': 'x=y'}


def test_A_parse_pairs_3():
    assert parse_pairs(' ; k = v ; ') == {'k': 'v'}


def test_B_percent_change_0():
    assert percent_change(50, 75) == 50.0


def test_B_percent_change_1():
    assert percent_change(0, 5) is None


def test_B_percent_change_2():
    assert percent_change(3, 2) == -33.3


def test_B_percent_change_3():
    assert percent_change(10, 10) == 0.0


def test_C_collapse_spaces_0():
    assert collapse_spaces(' a \t b\n') == 'a b'


def test_C_collapse_spaces_1():
    assert collapse_spaces('') == ''


def test_C_collapse_spaces_2():
    assert collapse_spaces('a  b   c') == 'a b c'


def test_C_collapse_spaces_3():
    assert collapse_spaces('\n\n') == ''


def test_G_top_k_0():
    assert top_k({'a': 1, 'b': 3, 'c': 3}, 2) == ['b', 'c']


def test_G_top_k_1():
    assert top_k({}, 3) == []


def test_G_top_k_2():
    assert top_k({'z': 2, 'y': 2, 'x': 1}, 5) == ['y', 'z', 'x']


def test_G_top_k_3():
    assert top_k({'a': 1}, 0) == []


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


def test_F_word_freq_0():
    assert word_freq('A b, a!') == {'a': 2, 'b': 1}


def test_F_word_freq_1():
    assert word_freq('') == {}


def test_F_word_freq_2():
    assert word_freq("don't stop") == {'don': 1, 't': 1, 'stop': 1}


def test_F_word_freq_3():
    assert word_freq('x1y') == {'x': 1, 'y': 1}


def test_E_split_tags_0():
    assert split_tags('a, b,,c ') == ['a', 'b', 'c']


def test_E_split_tags_1():
    assert split_tags('') == []


def test_E_split_tags_2():
    assert split_tags(' x ') == ['x']


def test_E_split_tags_3():
    assert split_tags('a;b') == ['a;b']


def test_DROPPED_slugify():
    with pytest.raises(NotImplementedError):
        slugify('Hello, World!')
