import importlib
import pytest

from canopy.slug import slugify
from canopy.codes import is_valid_code
from canopy.unique import dedupe
from canopy.change import percent_change
from canopy.words import word_freq
from canopy.naming import camel_to_snake
from canopy.legacy import split_tags
from canopy.spacing import collapse_spaces

def test_A_slugify_0():
    assert slugify('Hello, World!') == 'hello-world'


def test_A_slugify_1():
    assert slugify('--Már 2024 Plan--') == 'm-r-2024-plan'


def test_A_slugify_2():
    assert slugify('') == ''


def test_A_slugify_3():
    assert slugify('a__b..c') == 'a-b-c'


def test_A_slugify_4():
    assert slugify('ABC123') == 'abc123'


def test_B_is_valid_code_0():
    assert is_valid_code('AB-1234') is True


def test_B_is_valid_code_1():
    assert is_valid_code('AB-123') is False


def test_B_is_valid_code_2():
    assert is_valid_code(' AB-1234') is False


def test_B_is_valid_code_3():
    assert is_valid_code('A1-1234') is False


def test_B_is_valid_code_4():
    assert is_valid_code('ZZ-0000') is True


def test_B_is_valid_code_5():
    assert is_valid_code('AB_1234') is False


def test_C_dedupe_0():
    assert dedupe([3, 1, 3, 2, 1]) == [3, 1, 2]


def test_C_dedupe_1():
    assert dedupe([]) == []


def test_C_dedupe_2():
    assert dedupe(['b', 'a', 'b']) == ['b', 'a']


def test_G_percent_change_0():
    assert percent_change(50, 75) == 50.0


def test_G_percent_change_1():
    assert percent_change(0, 5) is None


def test_G_percent_change_2():
    assert percent_change(3, 2) == -33.3


def test_G_percent_change_3():
    assert percent_change(10, 10) == 0.0


def test_H_word_freq_0():
    assert word_freq('A b, a!') == {'a': 2, 'b': 1}


def test_H_word_freq_1():
    assert word_freq('') == {}


def test_H_word_freq_2():
    assert word_freq("don't stop") == {'don': 1, 't': 1, 'stop': 1}


def test_H_word_freq_3():
    assert word_freq('x1y') == {'x': 1, 'y': 1}


def test_F_camel_to_snake_0():
    assert camel_to_snake('parseHttpLine') == 'parse_http_line'


def test_F_camel_to_snake_1():
    assert camel_to_snake('Abc') == 'abc'


def test_F_camel_to_snake_2():
    assert camel_to_snake('aBC') == 'a_b_c'


def test_F_camel_to_snake_3():
    assert camel_to_snake('') == ''


def test_F_camel_to_snake_4():
    assert camel_to_snake('already_snake') == 'already_snake'


def test_E_split_tags_0():
    assert split_tags('a, b,,c ') == ['a', 'b', 'c']


def test_E_split_tags_1():
    assert split_tags('') == []


def test_E_split_tags_2():
    assert split_tags(' x ') == ['x']


def test_E_split_tags_3():
    assert split_tags('a;b') == ['a;b']


def test_DROPPED_collapse_spaces():
    with pytest.raises(NotImplementedError):
        collapse_spaces(' a \t b\n')
