import importlib
import pytest

from ember.ranking import top_k
from ember.spacing import collapse_spaces
from ember.bounds import clamp
from ember.intervals import merge_intervals
from ember.pairs import parse_pairs
from ember.words import word_freq
from ember.legacy import backoff_schedule
from ember.rle import rle_encode

def test_A_top_k_0():
    assert top_k({'a': 1, 'b': 3, 'c': 3}, 2) == ['b', 'c']


def test_A_top_k_1():
    assert top_k({}, 3) == []


def test_A_top_k_2():
    assert top_k({'z': 2, 'y': 2, 'x': 1}, 5) == ['y', 'z', 'x']


def test_A_top_k_3():
    assert top_k({'a': 1}, 0) == []


def test_B_collapse_spaces_0():
    assert collapse_spaces(' a \t b\n') == 'a b'


def test_B_collapse_spaces_1():
    assert collapse_spaces('') == ''


def test_B_collapse_spaces_2():
    assert collapse_spaces('a  b   c') == 'a b c'


def test_B_collapse_spaces_3():
    assert collapse_spaces('\n\n') == ''


def test_C_clamp_0():
    assert clamp(5, 0, 3) == 3


def test_C_clamp_1():
    assert clamp(-1, 0, 3) == 0


def test_C_clamp_2():
    assert clamp(2, 2, 2) == 2


def test_C_clamp_3():
    with pytest.raises(ValueError):
        clamp(1, 3, 0)


def test_G_merge_intervals_0():
    assert merge_intervals([(5, 6), (1, 3), (2, 4)]) == [(1, 4), (5, 6)]


def test_G_merge_intervals_1():
    assert merge_intervals([]) == []


def test_G_merge_intervals_2():
    assert merge_intervals([(1, 2), (2, 3)]) == [(1, 3)]


def test_G_merge_intervals_3():
    assert merge_intervals([(1, 10), (2, 3)]) == [(1, 10)]


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


def test_DROPPED_rle_encode():
    with pytest.raises(NotImplementedError):
        rle_encode('aaab')
