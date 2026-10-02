from nimbus.change import percent_change


def test_percent_change_0():
    assert percent_change(50, 75) == 50.0

def test_percent_change_1():
    assert percent_change(0, 5) is None
