import importlib
import pytest

from alder.slug import slugify
from alder.codes import is_valid_code
from alder.words import word_freq
from alder.bounds import clamp
from alder.numbers import extract_numbers
from alder.spacing import collapse_spaces
from alder.legacy import backoff_schedule
from alder.stats import moving_average

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


def test_C_word_freq_0():
    assert word_freq('A b, a!') == {'a': 2, 'b': 1}


def test_C_word_freq_1():
    assert word_freq('') == {}


def test_C_word_freq_2():
    assert word_freq("don't stop") == {'don': 1, 't': 1, 'stop': 1}


def test_C_word_freq_3():
    assert word_freq('x1y') == {'x': 1, 'y': 1}


def test_G_clamp_0():
    assert clamp(5, 0, 3) == 3


def test_G_clamp_1():
    assert clamp(-1, 0, 3) == 0


def test_G_clamp_2():
    assert clamp(2, 2, 2) == 2


def test_G_clamp_3():
    with pytest.raises(ValueError):
        clamp(1, 3, 0)


def test_H_extract_numbers_0():
    assert extract_numbers('a12b3') == [12, 3]


def test_H_extract_numbers_1():
    assert extract_numbers('-4.50') == [4, 50]


def test_H_extract_numbers_2():
    assert extract_numbers('') == []


def test_H_extract_numbers_3():
    assert extract_numbers('007x') == [7]


def test_H_extract_numbers_4():
    assert extract_numbers('1 2 3') == [1, 2, 3]


def test_F_collapse_spaces_0():
    assert collapse_spaces(' a \t b\n') == 'a b'


def test_F_collapse_spaces_1():
    assert collapse_spaces('') == ''


def test_F_collapse_spaces_2():
    assert collapse_spaces('a  b   c') == 'a b c'


def test_F_collapse_spaces_3():
    assert collapse_spaces('\n\n') == ''


def test_E_backoff_schedule_0():
    assert backoff_schedule() == [1, 2, 4]


def test_E_backoff_schedule_1():
    assert len(backoff_schedule()) == 3


def test_DROPPED_moving_average():
    with pytest.raises(NotImplementedError):
        moving_average([1, 2, 3, 4], 2)
