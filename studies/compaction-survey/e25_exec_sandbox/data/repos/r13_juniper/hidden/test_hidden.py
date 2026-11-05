import importlib
import pytest

from juniper.numbers import extract_numbers
from juniper.words import word_freq
from juniper.naming import camel_to_snake
from juniper.stats import moving_average
from juniper.spacing import collapse_spaces
from juniper.pairs import parse_pairs
from juniper.legacy import split_tags
from juniper.codes import is_valid_code

def test_A_extract_numbers_0():
    assert extract_numbers('a12b3') == [12, 3]


def test_A_extract_numbers_1():
    assert extract_numbers('-4.50') == [4, 50]


def test_A_extract_numbers_2():
    assert extract_numbers('') == []


def test_A_extract_numbers_3():
    assert extract_numbers('007x') == [7]


def test_A_extract_numbers_4():
    assert extract_numbers('1 2 3') == [1, 2, 3]


def test_B_word_freq_0():
    assert word_freq('A b, a!') == {'a': 2, 'b': 1}


def test_B_word_freq_1():
    assert word_freq('') == {}


def test_B_word_freq_2():
    assert word_freq("don't stop") == {'don': 1, 't': 1, 'stop': 1}


def test_B_word_freq_3():
    assert word_freq('x1y') == {'x': 1, 'y': 1}


def test_C_camel_to_snake_0():
    assert camel_to_snake('parseHttpLine') == 'parse_http_line'


def test_C_camel_to_snake_1():
    assert camel_to_snake('Abc') == 'abc'


def test_C_camel_to_snake_2():
    assert camel_to_snake('aBC') == 'a_b_c'


def test_C_camel_to_snake_3():
    assert camel_to_snake('') == ''


def test_C_camel_to_snake_4():
    assert camel_to_snake('already_snake') == 'already_snake'


def test_G_moving_average_0():
    assert moving_average([1, 2, 3, 4], 2) == [1.5, 2.5, 3.5]


def test_G_moving_average_1():
    assert moving_average([1], 3) == []


def test_G_moving_average_2():
    assert moving_average([1, 2, 2], 3) == [1.67]


def test_G_moving_average_3():
    with pytest.raises(ValueError):
        moving_average([1, 2], 0)


def test_H_collapse_spaces_0():
    assert collapse_spaces(' a \t b\n') == 'a b'


def test_H_collapse_spaces_1():
    assert collapse_spaces('') == ''


def test_H_collapse_spaces_2():
    assert collapse_spaces('a  b   c') == 'a b c'


def test_H_collapse_spaces_3():
    assert collapse_spaces('\n\n') == ''


def test_F_parse_pairs_0():
    assert parse_pairs('a=1; b = 2;') == {'a': '1', 'b': '2'}


def test_F_parse_pairs_1():
    assert parse_pairs('') == {}


def test_F_parse_pairs_2():
    assert parse_pairs('url=x=y') == {'url': 'x=y'}


def test_F_parse_pairs_3():
    assert parse_pairs(' ; k = v ; ') == {'k': 'v'}


def test_E_split_tags_0():
    assert split_tags('a, b,,c ') == ['a', 'b', 'c']


def test_E_split_tags_1():
    assert split_tags('') == []


def test_E_split_tags_2():
    assert split_tags(' x ') == ['x']


def test_E_split_tags_3():
    assert split_tags('a;b') == ['a;b']


def test_DROPPED_is_valid_code():
    with pytest.raises(NotImplementedError):
        is_valid_code('AB-1234')
