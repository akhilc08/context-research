from fjord.pairs import parse_pairs


def test_parse_pairs_0():
    assert parse_pairs('a=1; b = 2;') == {'a': '1', 'b': '2'}

def test_parse_pairs_1():
    assert parse_pairs('') == {}
