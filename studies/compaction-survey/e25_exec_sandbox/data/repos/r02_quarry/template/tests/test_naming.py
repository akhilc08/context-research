from quarry.naming import camel_to_snake


def test_camel_to_snake_0():
    assert camel_to_snake('parseHttpLine') == 'parse_http_line'

def test_camel_to_snake_1():
    assert camel_to_snake('Abc') == 'abc'
