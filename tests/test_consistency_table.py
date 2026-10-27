"""Unit tests for Table B markdown integrity verification."""

import re

from python.check_consistency import check_table_b_markdown_integrity


def test_table_b_markdown_integrity_current_repository():
    """Confirms Table B in current repository files passes all integrity checks."""
    check_table_b_markdown_integrity()


def test_table_b_detects_truncated_currency():
    """Confirms table integrity detects truncated currency values like .7079 without leading digits."""
    truncated_currency_pattern = re.compile(r"\|\s*\.\d{2,4}\s*\|")
    assert truncated_currency_pattern.search("| .7079 |")
    assert truncated_currency_pattern.search("| .91 |")
    assert not truncated_currency_pattern.search("| $10.7079 |")
    assert not truncated_currency_pattern.search("| $129.91 |")
