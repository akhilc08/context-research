import importlib
import pytest

from prairie.rle import rle_encode
from prairie.pairs import parse_pairs
from prairie.naming import camel_to_snake
from prairie.ranking import top_k
from prairie.slug import slugify
from prairie.words import word_freq
from prairie.legacy import split_tags
from prairie.bounds import clamp

def test_A_rle_encode_0():
    assert rle_encode('aaab') == 'a3b1'


def test_A_rle_encode_1():
    assert rle_encode('') == ''


def test_A_rle_encode_2():
    assert rle_encode('abba') == 'a1b2a1'


def test_A_rle_encode_3():
    assert rle_encode('zzzzzzzzzzzz') == 'z12'


def test_B_parse_pairs_0():
    assert parse_pairs('a=1; b = 2;') == {'a': '1', 'b': '2'}


def test_B_parse_pairs_1():
    assert parse_pairs('') == {}


def test_B_parse_pairs_2():
    assert parse_pairs('url=x=y') == {'url': 'x=y'}


def test_B_parse_pairs_3():
    assert parse_pairs(' ; k = v ; ') == {'k': 'v'}


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


def test_G_top_k_0():
    assert top_k({'a': 1, 'b': 3, 'c': 3}, 2) == ['b', 'c']


def test_G_top_k_1():
    assert top_k({}, 3) == []


def test_G_top_k_2():
    assert top_k({'z': 2, 'y': 2, 'x': 1}, 5) == ['y', 'z', 'x']


def test_G_top_k_3():
    assert top_k({'a': 1}, 0) == []


def test_H_slugify_0():
    assert slugify('Hello, World!') == 'hello-world'


def test_H_slugify_1():
    assert slugify('--Már 2024 Plan--') == 'm-r-2024-plan'


def test_H_slugify_2():
    assert slugify('') == ''


def test_H_slugify_3():
    assert slugify('a__b..c') == 'a-b-c'


def test_H_slugify_4():
    assert slugify('ABC123') == 'abc123'


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


def test_DROPPED_clamp():
    with pytest.raises(NotImplementedError):
        clamp(5, 0, 3)
