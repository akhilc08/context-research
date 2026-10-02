from nimbus.nesting import flatten


def test_flatten_0():
    assert flatten([1, [2, (3, [4])], 'ab']) == [1, 2, 3, 4, 'ab']

def test_flatten_1():
    assert flatten([]) == []
