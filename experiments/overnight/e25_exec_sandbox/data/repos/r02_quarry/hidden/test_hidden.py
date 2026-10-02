import importlib
import pytest

from quarry.ranking import top_k
from quarry.words import word_freq
from quarry.naming import camel_to_snake
from quarry.rotation import rotate
from quarry.pairs import parse_pairs
from quarry.slug import slugify
from quarry.legacy import backoff_schedule
from quarry.intervals import merge_intervals

def test_A_top_k_0():
    assert top_k({'a': 1, 'b': 3, 'c': 3}, 2) == ['b', 'c']


def test_A_top_k_1():
    assert top_k({}, 3) == []


def test_A_top_k_2():
    assert top_k({'z': 2, 'y': 2, 'x': 1}, 5) == ['y', 'z', 'x']


def test_A_top_k_3():
    assert top_k({'a': 1}, 0) == []


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


def test_G_rotate_0():
    assert rotate([1, 2, 3, 4], 1) == [4, 1, 2, 3]


def test_G_rotate_1():
    assert rotate([], 3) == []


def test_G_rotate_2():
    assert rotate([1, 2, 3], 4) == [3, 1, 2]


def test_G_rotate_3():
    assert rotate([1, 2, 3], -1) == [2, 3, 1]


def test_H_parse_pairs_0():
    assert parse_pairs('a=1; b = 2;') == {'a': '1', 'b': '2'}


def test_H_parse_pairs_1():
    assert parse_pairs('') == {}


def test_H_parse_pairs_2():
    assert parse_pairs('url=x=y') == {'url': 'x=y'}


def test_H_parse_pairs_3():
    assert parse_pairs(' ; k = v ; ') == {'k': 'v'}


def test_F_slugify_0():
    assert slugify('Hello, World!') == 'hello-world'


def test_F_slugify_1():
    assert slugify('--Már 2024 Plan--') == 'm-r-2024-plan'


def test_F_slugify_2():
    assert slugify('') == ''


def test_F_slugify_3():
    assert slugify('a__b..c') == 'a-b-c'


def test_F_slugify_4():
    assert slugify('ABC123') == 'abc123'


def test_E_backoff_schedule_0():
    assert backoff_schedule() == [1, 2, 4]


def test_E_backoff_schedule_1():
    assert len(backoff_schedule()) == 3


def test_DROPPED_merge_intervals():
    with pytest.raises(NotImplementedError):
        merge_intervals([(5, 6), (1, 3), (2, 4)])
