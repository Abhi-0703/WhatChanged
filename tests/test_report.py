"""Unit tests for ChangeReport and parse_report."""

import pytest
from whatchanged.report import ChangeReport, parse_report


def test_clean_json():
    raw = '{"changes": ["Water bottle added on the table"], "triggered_rule_ids": [0]}'
    report = parse_report(raw, n_rules=2)
    assert not report.parse_error
    assert report.changes == ["Water bottle added on the table"]
    assert report.triggered_rule_ids == [0]


def test_json_in_markdown_code_fences():
    raw = """Here is the result:
```json
{
  "changes": [
    "Drawer opened",
    "Book removed"
  ],
  "triggered_rule_ids": [1]
}
```
Hope this helps!"""
    report = parse_report(raw, n_rules=3)
    assert not report.parse_error
    assert report.changes == ["Drawer opened", "Book removed"]
    assert report.triggered_rule_ids == [1]


def test_json_with_extra_prose():
    raw = 'Based on the images: {"changes": ["Door opened"], "triggered_rule_ids": [0]} Nothing else changed.'
    report = parse_report(raw, n_rules=1)
    assert not report.parse_error
    assert report.changes == ["Door opened"]
    assert report.triggered_rule_ids == [0]


def test_out_of_range_rule_ids():
    raw = '{"changes": ["Laptop moved"], "triggered_rule_ids": [-1, 0, 5, 99]}'
    report = parse_report(raw, n_rules=2)  # Only 0 is valid for n_rules=2
    assert not report.parse_error
    assert report.changes == ["Laptop moved"]
    assert report.triggered_rule_ids == [0]


def test_garbage_text_returns_parse_error_no_raise():
    raw = "I cannot see any images, please provide more context or retry later."
    report = parse_report(raw, n_rules=2)
    assert report.parse_error
    assert report.changes == []
    assert report.triggered_rule_ids == []
    assert report.raw == raw


def test_empty_string():
    report = parse_report("", n_rules=1)
    assert report.parse_error
    assert report.changes == []
