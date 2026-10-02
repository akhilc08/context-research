import importlib
import pytest

from willow.unique import dedupe
from willow.slug import slugify
from willow.spacing import collapse_spaces
from willow.nesting import flatten
from willow.pairs import parse_pairs
from willow.words import word_freq
from willow.legacy import backoff_schedule
from willow.ranking import top_k

def test_A_dedupe_0():
    assert dedupe([3, 1, 3, 2, 1]) == [3, 1, 2]


def test_A_dedupe_1():
    assert dedupe([]) == []


def test_A_dedupe_2():
    assert dedupe(['b', 'a', 'b']) == ['b', 'a']


def test_B_slugify_0():
    assert slugify('Hello, World!') == 'hello-world'


def test_B_slugify_1():
    assert slugify('--Már 2024 Plan--') == 'm-r-2024-plan'


def test_B_slugify_2():
    assert slugify('') == ''


def test_B_slugify_3():
    assert slugify('a__b..c') == 'a-b-c'


def test_B_slugify_4():
    assert slugify('ABC123') == 'abc123'


def test_C_collapse_spaces_0():
    assert collapse_spaces(' a \t b\n') == 'a b'


def test_C_collapse_spaces_1():
    assert collapse_spaces('') == ''


def test_C_collapse_spaces_2():
    assert collapse_spaces('a  b   c') == 'a b c'


def test_C_collapse_spaces_3():
    assert collapse_spaces('\n\n') == ''


def test_G_flatten_0():
    assert flatten([1, [2, (3, [4])], 'ab']) == [1, 2, 3, 4, 'ab']


def test_G_flatten_1():
    assert flatten([]) == []


def test_G_flatten_2():
    assert flatten([[[]]]) == []


def test_G_flatten_3():
    assert flatten(((1,), [2])) == [1, 2]


def test_H_parse_pairs_0():
    assert parse_pairs('a=1; b = 2;') == {'a': '1', 'b': '2'}


def test_H_parse_pairs_1():
    assert parse_pairs('') == {}


def test_H_parse_pairs_2():
    assert parse_pairs('url=x=y') == {'url': 'x=y'}


def test_H_parse_pairs_3():
    assert parse_pairs(' ; k = v ; ') == {'k': 'v'}


def test_F_word_freq_0():
    assert word_freq('A b, a!') == {'a': 2, 'b': 1}


def test_F_word_freq_1():
    assert word_freq('') == {}


def test_F_word_freq_2():
    assert word_freq("don't stop") == {'don': 1, 't': 1, 'stop': 1}


def test_F_word_freq_3():
    assert word_freq('x1y') == {'x': 1, 'y': 1}


def test_E_backoff_schedule_0():
    assert backoff_schedule() == [1, 2, 4]


def test_E_backoff_schedule_1():
    assert len(backoff_schedule()) == 3


def test_DROPPED_top_k():
    with pytest.raises(NotImplementedError):
        top_k({'a': 1, 'b': 3, 'c': 3}, 2)
