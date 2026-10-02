import importlib
import pytest

from marlin.pairs import parse_pairs
from marlin.numbers import extract_numbers
from marlin.ranking import top_k
from marlin.slug import slugify
from marlin.naming import camel_to_snake
from marlin.spacing import collapse_spaces
from marlin.legacy import split_tags
from marlin.unique import dedupe

def test_A_parse_pairs_0():
    assert parse_pairs('a=1; b = 2;') == {'a': '1', 'b': '2'}


def test_A_parse_pairs_1():
    assert parse_pairs('') == {}


def test_A_parse_pairs_2():
    assert parse_pairs('url=x=y') == {'url': 'x=y'}


def test_A_parse_pairs_3():
    assert parse_pairs(' ; k = v ; ') == {'k': 'v'}


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


def test_C_top_k_0():
    assert top_k({'a': 1, 'b': 3, 'c': 3}, 2) == ['b', 'c']


def test_C_top_k_1():
    assert top_k({}, 3) == []


def test_C_top_k_2():
    assert top_k({'z': 2, 'y': 2, 'x': 1}, 5) == ['y', 'z', 'x']


def test_C_top_k_3():
    assert top_k({'a': 1}, 0) == []


def test_G_slugify_0():
    assert slugify('Hello, World!') == 'hello-world'


def test_G_slugify_1():
    assert slugify('--Már 2024 Plan--') == 'm-r-2024-plan'


def test_G_slugify_2():
    assert slugify('') == ''


def test_G_slugify_3():
    assert slugify('a__b..c') == 'a-b-c'


def test_G_slugify_4():
    assert slugify('ABC123') == 'abc123'


def test_H_camel_to_snake_0():
    assert camel_to_snake('parseHttpLine') == 'parse_http_line'


def test_H_camel_to_snake_1():
    assert camel_to_snake('Abc') == 'abc'


def test_H_camel_to_snake_2():
    assert camel_to_snake('aBC') == 'a_b_c'


def test_H_camel_to_snake_3():
    assert camel_to_snake('') == ''


def test_H_camel_to_snake_4():
    assert camel_to_snake('already_snake') == 'already_snake'


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


def test_DROPPED_dedupe():
    with pytest.raises(NotImplementedError):
        dedupe([3, 1, 3, 2, 1])
