import importlib
import pytest

from yarrow.ranking import top_k
from yarrow.words import word_freq
from yarrow.pairs import parse_pairs
from yarrow.rotation import rotate
from yarrow.slug import slugify
from yarrow.spacing import collapse_spaces
from yarrow.legacy import lookup
from yarrow.stats import moving_average

def test_A_top_k_0():
    assert top_k({'a': 1, 'b': 3, 'c': 3}, 2) == ['b', 'c']


def test_A_top_k_1():
    assert top_k({}, 3) == []


def test_A_top_k_2():
    assert top_k({'z': 2, 'y': 2, 'x': 1}, 5) == ['y', 'z', 'x']


def test_A_top_k_3():
    assert top_k({'a': 1}, 0) == []


def test_B_word_freq_0():
    assert word_freq('A b, a!') == {'a': 2, 'b': 1}


def test_B_word_freq_1():
    assert word_freq('') == {}


def test_B_word_freq_2():
    assert word_freq("don't stop") == {'don': 1, 't': 1, 'stop': 1}


def test_B_word_freq_3():
    assert word_freq('x1y') == {'x': 1, 'y': 1}


def test_C_parse_pairs_0():
    assert parse_pairs('a=1; b = 2;') == {'a': '1', 'b': '2'}


def test_C_parse_pairs_1():
    assert parse_pairs('') == {}


def test_C_parse_pairs_2():
    assert parse_pairs('url=x=y') == {'url': 'x=y'}


def test_C_parse_pairs_3():
    assert parse_pairs(' ; k = v ; ') == {'k': 'v'}


def test_G_rotate_0():
    assert rotate([1, 2, 3, 4], 1) == [4, 1, 2, 3]


def test_G_rotate_1():
    assert rotate([], 3) == []


def test_G_rotate_2():
    assert rotate([1, 2, 3], 4) == [3, 1, 2]


def test_G_rotate_3():
    assert rotate([1, 2, 3], -1) == [2, 3, 1]


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


def test_F_collapse_spaces_0():
    assert collapse_spaces(' a \t b\n') == 'a b'


def test_F_collapse_spaces_1():
    assert collapse_spaces('') == ''


def test_F_collapse_spaces_2():
    assert collapse_spaces('a  b   c') == 'a b c'


def test_F_collapse_spaces_3():
    assert collapse_spaces('\n\n') == ''


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
