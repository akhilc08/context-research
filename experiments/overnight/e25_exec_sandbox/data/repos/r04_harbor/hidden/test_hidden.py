import importlib
import pytest

from harbor.naming import camel_to_snake
from harbor.slug import slugify
from harbor.codes import is_valid_code
from harbor.unique import dedupe
from harbor.pairs import parse_pairs
from harbor.numbers import extract_numbers
from harbor.legacy import split_tags
from harbor.stats import moving_average

def test_A_camel_to_snake_0():
    assert camel_to_snake('parseHttpLine') == 'parse_http_line'


def test_A_camel_to_snake_1():
    assert camel_to_snake('Abc') == 'abc'


def test_A_camel_to_snake_2():
    assert camel_to_snake('aBC') == 'a_b_c'


def test_A_camel_to_snake_3():
    assert camel_to_snake('') == ''


def test_A_camel_to_snake_4():
    assert camel_to_snake('already_snake') == 'already_snake'


def test_B_slugify_0():
    assert slugify('Hello, World!') == 'hello-world'


def test_B_slugify_1():
    assert slugify('--Már 2024 Plan--') == 'm-r-2024-plan'


def test_B_slugify_2():
    assert slugify('') == ''


def test_B_slugify_3():
    assert slugify('a__b..c') == 'a-b-c'


def test_B_slugify_4():
    assert slugify('ABC123') == 'abc123'


def test_C_is_valid_code_0():
    assert is_valid_code('AB-1234') is True


def test_C_is_valid_code_1():
    assert is_valid_code('AB-123') is False


def test_C_is_valid_code_2():
    assert is_valid_code(' AB-1234') is False


def test_C_is_valid_code_3():
    assert is_valid_code('A1-1234') is False


def test_C_is_valid_code_4():
    assert is_valid_code('ZZ-0000') is True


def test_C_is_valid_code_5():
    assert is_valid_code('AB_1234') is False


def test_G_dedupe_0():
    assert dedupe([3, 1, 3, 2, 1]) == [3, 1, 2]


def test_G_dedupe_1():
    assert dedupe([]) == []


def test_G_dedupe_2():
    assert dedupe(['b', 'a', 'b']) == ['b', 'a']


def test_H_parse_pairs_0():
    assert parse_pairs('a=1; b = 2;') == {'a': '1', 'b': '2'}


def test_H_parse_pairs_1():
    assert parse_pairs('') == {}


def test_H_parse_pairs_2():
    assert parse_pairs('url=x=y') == {'url': 'x=y'}


def test_H_parse_pairs_3():
    assert parse_pairs(' ; k = v ; ') == {'k': 'v'}


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


def test_E_split_tags_0():
    assert split_tags('a, b,,c ') == ['a', 'b', 'c']


def test_E_split_tags_1():
    assert split_tags('') == []


def test_E_split_tags_2():
    assert split_tags(' x ') == ['x']


def test_E_split_tags_3():
    assert split_tags('a;b') == ['a;b']


def test_DROPPED_moving_average():
    with pytest.raises(NotImplementedError):
        moving_average([1, 2, 3, 4], 2)
