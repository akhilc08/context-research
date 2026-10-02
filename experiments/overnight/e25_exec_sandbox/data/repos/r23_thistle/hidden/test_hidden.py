import importlib
import pytest

from thistle.spacing import collapse_spaces
from thistle.intervals import merge_intervals
from thistle.numbers import extract_numbers
from thistle.chunking import chunk
from thistle.slug import slugify
from thistle.codes import is_valid_code
from thistle.legacy import backoff_schedule
from thistle.rle import rle_encode

def test_A_collapse_spaces_0():
    assert collapse_spaces(' a \t b\n') == 'a b'


def test_A_collapse_spaces_1():
    assert collapse_spaces('') == ''


def test_A_collapse_spaces_2():
    assert collapse_spaces('a  b   c') == 'a b c'


def test_A_collapse_spaces_3():
    assert collapse_spaces('\n\n') == ''


def test_B_merge_intervals_0():
    assert merge_intervals([(5, 6), (1, 3), (2, 4)]) == [(1, 4), (5, 6)]


def test_B_merge_intervals_1():
    assert merge_intervals([]) == []


def test_B_merge_intervals_2():
    assert merge_intervals([(1, 2), (2, 3)]) == [(1, 3)]


def test_B_merge_intervals_3():
    assert merge_intervals([(1, 10), (2, 3)]) == [(1, 10)]


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


def test_G_chunk_0():
    assert chunk([1, 2, 3], 2) == [[1, 2], [3]]


def test_G_chunk_1():
    assert chunk([], 3) == []


def test_G_chunk_2():
    assert chunk([1, 2], 5) == [[1, 2]]


def test_G_chunk_3():
    with pytest.raises(ValueError):
        chunk([1], 0)


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


def test_F_is_valid_code_0():
    assert is_valid_code('AB-1234') is True


def test_F_is_valid_code_1():
    assert is_valid_code('AB-123') is False


def test_F_is_valid_code_2():
    assert is_valid_code(' AB-1234') is False


def test_F_is_valid_code_3():
    assert is_valid_code('A1-1234') is False


def test_F_is_valid_code_4():
    assert is_valid_code('ZZ-0000') is True


def test_F_is_valid_code_5():
    assert is_valid_code('AB_1234') is False


def test_E_backoff_schedule_0():
    assert backoff_schedule() == [1, 2, 4]


def test_E_backoff_schedule_1():
    assert len(backoff_schedule()) == 3


def test_DROPPED_rle_encode():
    with pytest.raises(NotImplementedError):
        rle_encode('aaab')
