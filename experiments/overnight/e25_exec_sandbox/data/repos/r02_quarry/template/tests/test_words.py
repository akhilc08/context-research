from quarry.words import word_freq


def test_word_freq_0():
    assert word_freq('A b, a!') == {'a': 2, 'b': 1}

def test_word_freq_1():
    assert word_freq('') == {}
