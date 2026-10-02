import importlib
import pytest

from cedar.rotation import rotate
from cedar.codes import is_valid_code
from cedar.spacing import collapse_spaces
from cedar.rle import rle_encode
from cedar.slug import slugify
from cedar.pairs import parse_pairs
from cedar.legacy import split_tags
from cedar.change import percent_change

def test_A_rotate_0():
    assert rotate([1, 2, 3, 4], 1) == [4, 1, 2, 3]


def test_A_rotate_1():
    assert rotate([], 3) == []


def test_A_rotate_2():
    assert rotate([1, 2, 3], 4) == [3, 1, 2]


def test_A_rotate_3():
    assert rotate([1, 2, 3], -1) == [2, 3, 1]


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


def test_C_collapse_spaces_0():
    assert collapse_spaces(' a \t b\n') == 'a b'


def test_C_collapse_spaces_1():
    assert collapse_spaces('') == ''


def test_C_collapse_spaces_2():
    assert collapse_spaces('a  b   c') == 'a b c'


def test_C_collapse_spaces_3():
    assert collapse_spaces('\n\n') == ''


def test_G_rle_encode_0():
    assert rle_encode('aaab') == 'a3b1'


def test_G_rle_encode_1():
    assert rle_encode('') == ''


def test_G_rle_encode_2():
    assert rle_encode('abba') == 'a1b2a1'


def test_G_rle_encode_3():
    assert rle_encode('zzzzzzzzzzzz') == 'z12'


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


def test_F_parse_pairs_0():
    assert parse_pairs('a=1; b = 2;') == {'a': '1', 'b': '2'}


def test_F_parse_pairs_1():
    assert parse_pairs('') == {}


def test_F_parse_pairs_2():
    assert parse_pairs('url=x=y') == {'url': 'x=y'}


def test_F_parse_pairs_3():
    assert parse_pairs(' ; k = v ; ') == {'k': 'v'}


def test_E_split_tags_0():
    assert split_tags('a, b,,c ') == ['a', 'b', 'c']


def test_E_split_tags_1():
    assert split_tags('') == []


def test_E_split_tags_2():
    assert split_tags(' x ') == ['x']


def test_E_split_tags_3():
    assert split_tags('a;b') == ['a;b']


def test_DROPPED_percent_change():
    with pytest.raises(NotImplementedError):
        percent_change(50, 75)
