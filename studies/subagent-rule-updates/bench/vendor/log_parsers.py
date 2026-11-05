# Vendored from https://github.com/SWE-rebench/SWE-rebench-V2
# Path: lib/agent/log_parsers.py (parse_log_pytest only; the other parsers are not vendored)
# Commit: c71902a8cf8d2b725f63d51f199f4d3e56f68d2d
# License: MIT, see LICENSE in this folder.
# Changed from upstream: the TestStatus import path only.
from bench.vendor.swe_constants import TestStatus


def parse_log_pytest(log: str) -> dict[str, str]:
    """
    Parser for test logs generated with PyTest framework

    Args:
        log (str): log content
    Returns:
        dict: test case to test status mapping
    """
    test_status_map = {}
    for line in log.split("\n"):
        if any(line.startswith(x.value) for x in TestStatus):
            # Additional parsing for FAILED status
            if line.startswith(TestStatus.FAILED.value):
                line = line.replace(" - ", " ")
            test_case = line.split()
            if len(test_case) <= 1:
                continue
            test_status_map[test_case[1]] = test_case[0]
    return test_status_map
