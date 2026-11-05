import importlib
import pytest

from inlet.bounds import clamp
from inlet.codes import is_valid_code
from inlet.numbers import extract_numbers
from inlet.stats import moving_average
from inlet.naming import camel_to_snake
from inlet.slug import slugify
from inlet.legacy import lookup
from inlet.intervals import merge_intervals

def test_A_clamp_0():
    assert clamp(5, 0, 3) == 3


def test_A_clamp_1():
    assert clamp(-1, 0, 3) == 0


def test_A_clamp_2():
    assert clamp(2, 2, 2) == 2


def test_A_clamp_3():
    with pytest.raises(ValueError):
        clamp(1, 3, 0)


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


def test_E_lookup_0():
    assert lookup({'Alpha': 1}, ' alpha ') == 1


def test_E_lookup_1():
    assert lookup({'b': 2}, 'B') == 2


def test_E_lookup_2():
    assert lookup({}, 'x', 0) == 0


def test_E_lookup_3():
    assert lookup({'a': 1}, 'b') is None


def test_DROPPED_merge_intervals():
    with pytest.raises(NotImplementedError):
        merge_intervals([(5, 6), (1, 3), (2, 4)])
