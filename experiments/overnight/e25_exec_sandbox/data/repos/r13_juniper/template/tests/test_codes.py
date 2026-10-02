from juniper.codes import is_valid_code


def test_is_valid_code_0():
    assert is_valid_code('AB-1234') is True

def test_is_valid_code_1():
    assert is_valid_code('ab-1234') is False
