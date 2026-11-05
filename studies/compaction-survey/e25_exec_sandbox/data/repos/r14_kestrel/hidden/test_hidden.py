import importlib
import pytest

from kestrel.numbers import extract_numbers
from kestrel.rle import rle_encode
from kestrel.change import percent_change
from kestrel.nesting import flatten
from kestrel.codes import is_valid_code
from kestrel.pairs import parse_pairs
from kestrel.legacy import backoff_schedule
from kestrel.naming import camel_to_snake

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


def test_C_percent_change_0():
    assert percent_change(50, 75) == 50.0


def test_C_percent_change_1():
    assert percent_change(0, 5) is None


def test_C_percent_change_2():
    assert percent_change(3, 2) == -33.3


def test_C_percent_change_3():
    assert percent_change(10, 10) == 0.0


def test_G_flatten_0():
    assert flatten([1, [2, (3, [4])], 'ab']) == [1, 2, 3, 4, 'ab']


def test_G_flatten_1():
    assert flatten([]) == []


def test_G_flatten_2():
    assert flatten([[[]]]) == []


def test_G_flatten_3():
    assert flatten(((1,), [2])) == [1, 2]


def test_H_is_valid_code_0():
    assert is_valid_code('AB-1234') is True


def test_H_is_valid_code_1():
    assert is_valid_code('AB-123') is False


def test_H_is_valid_code_2():
    assert is_valid_code(' AB-1234') is False


def test_H_is_valid_code_3():
    assert is_valid_code('A1-1234') is False


def test_H_is_valid_code_4():
    assert is_valid_code('ZZ-0000') is True


def test_H_is_valid_code_5():
    assert is_valid_code('AB_1234') is False


def test_F_parse_pairs_0():
    assert parse_pairs('a=1; b = 2;') == {'a': '1', 'b': '2'}


def test_F_parse_pairs_1():
    assert parse_pairs('') == {}


def test_F_parse_pairs_2():
    assert parse_pairs('url=x=y') == {'url': 'x=y'}


def test_F_parse_pairs_3():
    assert parse_pairs(' ; k = v ; ') == {'k': 'v'}


def test_E_backoff_schedule_0():
    assert backoff_schedule() == [1, 2, 4]


def test_E_backoff_schedule_1():
    assert len(backoff_schedule()) == 3


def test_DROPPED_camel_to_snake():
    with pytest.raises(NotImplementedError):
        camel_to_snake('parseHttpLine')
