import importlib
import pytest

from quill.numbers import extract_numbers
from quill.rle import rle_encode
from quill.pairs import parse_pairs
from quill.spacing import collapse_spaces
from quill.naming import camel_to_snake
from quill.codes import is_valid_code
from quill.legacy import backoff_schedule
from quill.stats import moving_average

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


def test_C_parse_pairs_0():
    assert parse_pairs('a=1; b = 2;') == {'a': '1', 'b': '2'}


def test_C_parse_pairs_1():
    assert parse_pairs('') == {}


def test_C_parse_pairs_2():
    assert parse_pairs('url=x=y') == {'url': 'x=y'}


def test_C_parse_pairs_3():
    assert parse_pairs(' ; k = v ; ') == {'k': 'v'}


def test_G_collapse_spaces_0():
    assert collapse_spaces(' a \t b\n') == 'a b'


def test_G_collapse_spaces_1():
    assert collapse_spaces('') == ''


def test_G_collapse_spaces_2():
    assert collapse_spaces('a  b   c') == 'a b c'


def test_G_collapse_spaces_3():
    assert collapse_spaces('\n\n') == ''


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


def test_DROPPED_moving_average():
    with pytest.raises(NotImplementedError):
        moving_average([1, 2, 3, 4], 2)
