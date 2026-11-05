from meadow.legacy import lookup


def test_lookup_case():
    assert lookup({'Alpha': 1}, ' alpha ') == 1


def test_lookup_default():
    assert lookup({}, 'x', 0) == 0
