import importlib
import pytest

from beacon.intervals import merge_intervals
from beacon.codes import is_valid_code
from beacon.unique import dedupe
from beacon.ranking import top_k
from beacon.pairs import parse_pairs
from beacon.slug import slugify
from beacon.legacy import split_tags
from beacon.rle import rle_encode

def test_A_merge_intervals_0():
    assert merge_intervals([(5, 6), (1, 3), (2, 4)]) == [(1, 4), (5, 6)]


def test_A_merge_intervals_1():
    assert merge_intervals([]) == []


def test_A_merge_intervals_2():
    assert merge_intervals([(1, 2), (2, 3)]) == [(1, 3)]


def test_A_merge_intervals_3():
    assert merge_intervals([(1, 10), (2, 3)]) == [(1, 10)]


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


def test_C_dedupe_0():
    assert dedupe([3, 1, 3, 2, 1]) == [3, 1, 2]


def test_C_dedupe_1():
    assert dedupe([]) == []


def test_C_dedupe_2():
    assert dedupe(['b', 'a', 'b']) == ['b', 'a']


def test_G_top_k_0():
    assert top_k({'a': 1, 'b': 3, 'c': 3}, 2) == ['b', 'c']


def test_G_top_k_1():
    assert top_k({}, 3) == []


def test_G_top_k_2():
    assert top_k({'z': 2, 'y': 2, 'x': 1}, 5) == ['y', 'z', 'x']


def test_G_top_k_3():
    assert top_k({'a': 1}, 0) == []


def test_H_parse_pairs_0():
    assert parse_pairs('a=1; b = 2;') == {'a': '1', 'b': '2'}


def test_H_parse_pairs_1():
    assert parse_pairs('') == {}


def test_H_parse_pairs_2():
    assert parse_pairs('url=x=y') == {'url': 'x=y'}


def test_H_parse_pairs_3():
    assert parse_pairs(' ; k = v ; ') == {'k': 'v'}


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


def test_DROPPED_rle_encode():
    with pytest.raises(NotImplementedError):
        rle_encode('aaab')
