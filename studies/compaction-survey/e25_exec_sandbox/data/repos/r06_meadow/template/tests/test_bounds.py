from meadow.bounds import clamp


def test_clamp_0():
    assert clamp(5, 0, 3) == 3

def test_clamp_1():
    assert clamp(-1, 0, 3) == 0
