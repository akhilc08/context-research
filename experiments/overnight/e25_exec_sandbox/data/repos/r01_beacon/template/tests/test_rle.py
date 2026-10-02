from beacon.rle import rle_encode


def test_rle_encode_0():
    assert rle_encode('aaab') == 'a3b1'

def test_rle_encode_1():
    assert rle_encode('') == ''
