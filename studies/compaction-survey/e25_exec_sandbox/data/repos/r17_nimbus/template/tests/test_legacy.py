from nimbus.legacy import backoff_schedule


def test_backoff():
    assert backoff_schedule() == [1, 2, 4]
