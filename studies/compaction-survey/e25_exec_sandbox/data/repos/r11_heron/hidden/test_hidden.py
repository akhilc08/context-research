import importlib
import pytest

from heron.chunking import chunk
from heron.ranking import top_k
from heron.numbers import extract_numbers
from heron.codes import is_valid_code
from heron.slug import slugify
from heron.words import word_freq
from heron.legacy import backoff_schedule
from heron.spacing import collapse_spaces

def test_A_chunk_0():
    assert chunk([1, 2, 3], 2) == [[1, 2], [3]]


def test_A_chunk_1():
    assert chunk([], 3) == []


def test_A_chunk_2():
    assert chunk([1, 2], 5) == [[1, 2]]


def test_A_chunk_3():
    with pytest.raises(ValueError):
        chunk([1], 0)


def test_B_top_k_0():
    assert top_k({'a': 1, 'b': 3, 'c': 3}, 2) == ['b', 'c']


def test_B_top_k_1():
    assert top_k({}, 3) == []


def test_B_top_k_2():
    assert top_k({'z': 2, 'y': 2, 'x': 1}, 5) == ['y', 'z', 'x']


def test_B_top_k_3():
    assert top_k({'a': 1}, 0) == []


def test_C_extract_numbers_0():
    assert extract_numbers('a12b3') == [12, 3]


def test_C_extract_numbers_1():
    assert extract_numbers('-4.50') == [4, 50]


def test_C_extract_numbers_2():
    assert extract_numbers('') == []


def test_C_extract_numbers_3():
    assert extract_numbers('007x') == [7]


def test_C_extract_numbers_4():
    assert extract_numbers('1 2 3') == [1, 2, 3]


def test_G_is_valid_code_0():
    assert is_valid_code('AB-1234') is True


def test_G_is_valid_code_1():
    assert is_valid_code('AB-123') is False


def test_G_is_valid_code_2():
    assert is_valid_code(' AB-1234') is False


def test_G_is_valid_code_3():
    assert is_valid_code('A1-1234') is False


def test_G_is_valid_code_4():
    assert is_valid_code('ZZ-0000') is True


def test_G_is_valid_code_5():
    assert is_valid_code('AB_1234') is False


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


def test_E_backoff_schedule_0():
    assert backoff_schedule() == [1, 2, 4]


def test_E_backoff_schedule_1():
    assert len(backoff_schedule()) == 3


def test_DROPPED_collapse_spaces():
    with pytest.raises(NotImplementedError):
        collapse_spaces(' a \t b\n')
