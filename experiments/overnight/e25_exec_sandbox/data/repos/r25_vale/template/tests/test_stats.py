from vale.stats import moving_average


def test_moving_average_0():
    assert moving_average([1, 2, 3, 4], 2) == [1.5, 2.5, 3.5]

def test_moving_average_1():
    assert moving_average([1], 3) == []
