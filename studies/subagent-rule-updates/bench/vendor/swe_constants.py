# Vendored from https://github.com/SWE-rebench/SWE-rebench-V2
# Path: lib/agent/swe_constants.py (TestStatus only)
# Commit: c71902a8cf8d2b725f63d51f199f4d3e56f68d2d
# License: MIT, see LICENSE in this folder.
from enum import Enum


class TestStatus(str, Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    ERROR = "ERROR"
