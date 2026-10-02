import importlib
import pytest

from ridge.spacing import collapse_spaces
from ridge.rle import rle_encode
from ridge.change import percent_change
from ridge.pairs import parse_pairs
from ridge.naming import camel_to_snake
from ridge.codes import is_valid_code
from ridge.legacy import lookup
from ridge.stats import moving_average

def test_A_collapse_spaces_0():
    assert collapse_spaces(' a \t b\n') == 'a b'


def test_A_collapse_spaces_1():
    assert collapse_spaces('') == ''


def test_A_collapse_spaces_2():
    assert collapse_spaces('a  b   c') == 'a b c'


def test_A_collapse_spaces_3():
    assert collapse_spaces('\n\n') == ''


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


def test_G_parse_pairs_0():
    assert parse_pairs('a=1; b = 2;') == {'a': '1', 'b': '2'}


def test_G_parse_pairs_1():
    assert parse_pairs('') == {}


def test_G_parse_pairs_2():
    assert parse_pairs('url=x=y') == {'url': 'x=y'}


def test_G_parse_pairs_3():
    assert parse_pairs(' ; k = v ; ') == {'k': 'v'}


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


def test_E_lookup_0():
    assert lookup({'Alpha': 1}, ' alpha ') == 1


def test_E_lookup_1():
    assert lookup({'b': 2}, 'B') == 2


def test_E_lookup_2():
    assert lookup({}, 'x', 0) == 0


def test_E_lookup_3():
    assert lookup({'a': 1}, 'b') is None


def test_DROPPED_moving_average():
    with pytest.raises(NotImplementedError):
        moving_average([1, 2, 3, 4], 2)
