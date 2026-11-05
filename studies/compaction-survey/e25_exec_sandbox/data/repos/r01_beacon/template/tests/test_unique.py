from beacon.unique import dedupe


def test_dedupe_0():
    assert dedupe([3, 1, 3, 2, 1]) == [3, 1, 2]

def test_dedupe_1():
    assert dedupe([]) == []
