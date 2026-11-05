import importlib
import pytest

from tundra.numbers import extract_numbers
from tundra.chunking import chunk
from tundra.nesting import flatten
from tundra.pairs import parse_pairs
from tundra.slug import slugify
from tundra.naming import camel_to_snake
from tundra.legacy import backoff_schedule
from tundra.words import word_freq

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


def test_B_chunk_0():
    assert chunk([1, 2, 3], 2) == [[1, 2], [3]]


def test_B_chunk_1():
    assert chunk([], 3) == []


def test_B_chunk_2():
    assert chunk([1, 2], 5) == [[1, 2]]


def test_B_chunk_3():
    with pytest.raises(ValueError):
        chunk([1], 0)


def test_C_flatten_0():
    assert flatten([1, [2, (3, [4])], 'ab']) == [1, 2, 3, 4, 'ab']


def test_C_flatten_1():
    assert flatten([]) == []


def test_C_flatten_2():
    assert flatten([[[]]]) == []


def test_C_flatten_3():
    assert flatten(((1,), [2])) == [1, 2]


def test_G_parse_pairs_0():
    assert parse_pairs('a=1; b = 2;') == {'a': '1', 'b': '2'}


def test_G_parse_pairs_1():
    assert parse_pairs('') == {}


def test_G_parse_pairs_2():
    assert parse_pairs('url=x=y') == {'url': 'x=y'}


def test_G_parse_pairs_3():
    assert parse_pairs(' ; k = v ; ') == {'k': 'v'}


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


def test_E_backoff_schedule_0():
    assert backoff_schedule() == [1, 2, 4]


def test_E_backoff_schedule_1():
    assert len(backoff_schedule()) == 3


def test_DROPPED_word_freq():
    with pytest.raises(NotImplementedError):
        word_freq('A b, a!')
