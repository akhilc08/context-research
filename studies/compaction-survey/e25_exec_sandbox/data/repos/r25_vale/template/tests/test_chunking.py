from vale.chunking import chunk


def test_chunk_0():
    assert chunk([1, 2, 3], 2) == [[1, 2], [3]]

def test_chunk_1():
    assert chunk([], 3) == []
