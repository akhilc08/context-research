from orchard.numbers import extract_numbers


def test_extract_numbers_0():
    assert extract_numbers('a12b3') == [12, 3]

def test_extract_numbers_1():
    assert extract_numbers('none') == []
