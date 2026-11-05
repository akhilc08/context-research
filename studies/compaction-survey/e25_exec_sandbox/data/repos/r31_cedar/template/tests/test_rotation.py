from cedar.rotation import rotate


def test_rotate_0():
    assert rotate([1, 2, 3, 4], 1) == [4, 1, 2, 3]

def test_rotate_1():
    assert rotate([], 3) == []
