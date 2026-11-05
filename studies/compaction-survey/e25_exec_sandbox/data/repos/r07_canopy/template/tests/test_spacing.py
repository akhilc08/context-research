from canopy.spacing import collapse_spaces


def test_collapse_spaces_0():
    assert collapse_spaces(' a \t b\n') == 'a b'

def test_collapse_spaces_1():
    assert collapse_spaces('x') == 'x'
