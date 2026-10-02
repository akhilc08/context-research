import importlib
import pytest

from vale.numbers import extract_numbers
from vale.rle import rle_encode
from vale.chunking import chunk
from vale.stats import moving_average
from vale.naming import camel_to_snake
from vale.slug import slugify
from vale.legacy import split_tags
from vale.nesting import flatten

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


def test_B_rle_encode_0():
    assert rle_encode('aaab') == 'a3b1'


def test_B_rle_encode_1():
    assert rle_encode('') == ''


def test_B_rle_encode_2():
    assert rle_encode('abba') == 'a1b2a1'


def test_B_rle_encode_3():
    assert rle_encode('zzzzzzzzzzzz') == 'z12'


def test_C_chunk_0():
    assert chunk([1, 2, 3], 2) == [[1, 2], [3]]


def test_C_chunk_1():
    assert chunk([], 3) == []


def test_C_chunk_2():
    assert chunk([1, 2], 5) == [[1, 2]]


def test_C_chunk_3():
    with pytest.raises(ValueError):
        chunk([1], 0)


def test_G_moving_average_0():
    assert moving_average([1, 2, 3, 4], 2) == [1.5, 2.5, 3.5]


def test_G_moving_average_1():
    assert moving_average([1], 3) == []


def test_G_moving_average_2():
    assert moving_average([1, 2, 2], 3) == [1.67]


def test_G_moving_average_3():
    with pytest.raises(ValueError):
        moving_average([1, 2], 0)


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


def test_E_split_tags_0():
    assert split_tags('a, b,,c ') == ['a', 'b', 'c']


def test_E_split_tags_1():
    assert split_tags('') == []


def test_E_split_tags_2():
    assert split_tags(' x ') == ['x']


def test_E_split_tags_3():
    assert split_tags('a;b') == ['a;b']


def test_DROPPED_flatten():
    with pytest.raises(NotImplementedError):
        flatten([1, [2, (3, [4])], 'ab'])
