import importlib
import pytest

from lattice.chunking import chunk
from lattice.numbers import extract_numbers
from lattice.codes import is_valid_code
from lattice.nesting import flatten
from lattice.naming import camel_to_snake
from lattice.words import word_freq
from lattice.legacy import lookup
from lattice.slug import slugify

def test_A_chunk_0():
    assert chunk([1, 2, 3], 2) == [[1, 2], [3]]


def test_A_chunk_1():
    assert chunk([], 3) == []


def test_A_chunk_2():
    assert chunk([1, 2], 5) == [[1, 2]]


def test_A_chunk_3():
    with pytest.raises(ValueError):
        chunk([1], 0)


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


def test_G_flatten_0():
    assert flatten([1, [2, (3, [4])], 'ab']) == [1, 2, 3, 4, 'ab']


def test_G_flatten_1():
    assert flatten([]) == []


def test_G_flatten_2():
    assert flatten([[[]]]) == []


def test_G_flatten_3():
    assert flatten(((1,), [2])) == [1, 2]


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


def test_F_word_freq_0():
    assert word_freq('A b, a!') == {'a': 2, 'b': 1}


def test_F_word_freq_1():
    assert word_freq('') == {}


def test_F_word_freq_2():
    assert word_freq("don't stop") == {'don': 1, 't': 1, 'stop': 1}


def test_F_word_freq_3():
    assert word_freq('x1y') == {'x': 1, 'y': 1}


def test_E_lookup_0():
    assert lookup({'Alpha': 1}, ' alpha ') == 1


def test_E_lookup_1():
    assert lookup({'b': 2}, 'B') == 2


def test_E_lookup_2():
    assert lookup({}, 'x', 0) == 0


def test_E_lookup_3():
    assert lookup({'a': 1}, 'b') is None


def test_DROPPED_slugify():
    with pytest.raises(NotImplementedError):
        slugify('Hello, World!')
