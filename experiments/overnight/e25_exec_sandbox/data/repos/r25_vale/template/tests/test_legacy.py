from vale.legacy import split_tags


def test_split_tags():
    assert split_tags('a, b,,c ') == ['a', 'b', 'c']


def test_split_empty():
    assert split_tags('') == []
