from orchard.intervals import merge_intervals


def test_merge_intervals_0():
    assert merge_intervals([(5, 6), (1, 3), (2, 4)]) == [(1, 4), (5, 6)]

def test_merge_intervals_1():
    assert merge_intervals([]) == []
