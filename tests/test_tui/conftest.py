"""
TUI test configuration.

All tests in this directory are marked as TUI tests.
"""

import pytest


def pytest_collection_modifyitems(items):
    """Mark all tests in this directory as TUI tests."""
    for item in items:
        # Check if the test is in the test_tui directory
        if "/test_tui/" in str(item.fspath):
            item.add_marker(pytest.mark.tui)
