import importlib
import pytest

from glacier.pairs import parse_pairs
from glacier.change import percent_change
from glacier.chunking import chunk
from glacier.ranking import top_k
from glacier.naming import camel_to_snake
from glacier.spacing import collapse_spaces
from glacier.legacy import split_tags
from glacier.intervals import merge_intervals

def test_A_parse_pairs_0():
    assert parse_pairs('a=1; b = 2;') == {'a': '1', 'b': '2'}


def test_A_parse_pairs_1():
    assert parse_pairs('') == {}


def test_A_parse_pairs_2():
    assert parse_pairs('url=x=y') == {'url': 'x=y'}


def test_A_parse_pairs_3():
    assert parse_pairs(' ; k = v ; ') == {'k': 'v'}


def test_B_percent_change_0():
    assert percent_change(50, 75) == 50.0


def test_B_percent_change_1():
    assert percent_change(0, 5) is None


def test_B_percent_change_2():
    assert percent_change(3, 2) == -33.3


def test_B_percent_change_3():
    assert percent_change(10, 10) == 0.0


def test_C_chunk_0():
    assert chunk([1, 2, 3], 2) == [[1, 2], [3]]


def test_C_chunk_1():
    assert chunk([], 3) == []


def test_C_chunk_2():
    assert chunk([1, 2], 5) == [[1, 2]]


def test_C_chunk_3():
    with pytest.raises(ValueError):
        chunk([1], 0)


def test_G_top_k_0():
    assert top_k({'a': 1, 'b': 3, 'c': 3}, 2) == ['b', 'c']


def test_G_top_k_1():
    assert top_k({}, 3) == []


def test_G_top_k_2():
    assert top_k({'z': 2, 'y': 2, 'x': 1}, 5) == ['y', 'z', 'x']


def test_G_top_k_3():
    assert top_k({'a': 1}, 0) == []


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


def test_F_collapse_spaces_0():
    assert collapse_spaces(' a \t b\n') == 'a b'


def test_F_collapse_spaces_1():
    assert collapse_spaces('') == ''


def test_F_collapse_spaces_2():
    assert collapse_spaces('a  b   c') == 'a b c'


def test_F_collapse_spaces_3():
    assert collapse_spaces('\n\n') == ''


def test_E_split_tags_0():
    assert split_tags('a, b,,c ') == ['a', 'b', 'c']


def test_E_split_tags_1():
    assert split_tags('') == []


def test_E_split_tags_2():
    assert split_tags(' x ') == ['x']


def test_E_split_tags_3():
    assert split_tags('a;b') == ['a;b']


def test_DROPPED_merge_intervals():
    with pytest.raises(NotImplementedError):
        merge_intervals([(5, 6), (1, 3), (2, 4)])
