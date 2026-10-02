from bramble.slug import slugify


def test_slugify_0():
    assert slugify('Hello, World!') == 'hello-world'

def test_slugify_1():
    assert slugify('  A  b ') == 'a-b'
