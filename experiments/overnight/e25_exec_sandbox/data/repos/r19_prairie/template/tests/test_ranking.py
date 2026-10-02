from prairie.ranking import top_k


def test_top_k_0():
    assert top_k({'a': 1, 'b': 3, 'c': 3}, 2) == ['b', 'c']

def test_top_k_1():
    assert top_k({}, 3) == []
