"""ChangeReport dataclass and robust JSON parser for What Changed?."""

from dataclasses import dataclass, field
import json
import re
from typing import Any, List


@dataclass
class ChangeReport:
    """Structured report produced by the vision-language model."""

    changes: list[str] = field(default_factory=list)
    triggered_rule_ids: list[int] = field(default_factory=list)
    raw: str = ""
    parse_error: bool = False


def _find_json_object(text: str) -> str:
    """Finds the first balanced or outermost JSON object {...} in text."""
    # First, strip markdown fences if present
    stripped = re.sub(r"```(?:json)?\s*([\s\S]*?)\s*```", r"\1", text)

    # Look for the first { and the last }
    first_brace = stripped.find("{")
    if first_brace == -1:
        return ""

    # Count braces to find matching closing brace
    depth = 0
    in_string = False
    escape = False

    for i in range(first_brace, len(stripped)):
        ch = stripped[i]
        if escape:
            escape = False
            continue
        if ch == "\\":
            escape = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if not in_string:
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    return stripped[first_brace : i + 1]

    # Fallback: substring from first { to last }
    last_brace = stripped.rfind("}")
    if last_brace > first_brace:
        return stripped[first_brace : last_brace + 1]

    return ""


def parse_report(text: str, n_rules: int) -> ChangeReport:
    """Parses model output text into a structured ChangeReport.

    Handles:
    - Clean JSON
    - JSON enclosed in markdown code fences
    - Extra conversational text before/after JSON
    - Unsanitized rule indexes
    - Total garbage text (returns parse_error=True without crashing)
    """
    raw = text or ""
    if not raw.strip():
        return ChangeReport(raw=raw, parse_error=True)

    json_str = _find_json_object(raw)
    if not json_str:
        return ChangeReport(raw=raw, parse_error=True)

    try:
        data: Any = json.loads(json_str)
        if not isinstance(data, dict):
            return ChangeReport(raw=raw, parse_error=True)

        raw_changes = data.get("changes", [])
        changes: list[str] = []
        if isinstance(raw_changes, list):
            for item in raw_changes:
                if isinstance(item, str) and item.strip():
                    changes.append(item.strip())
                elif item is not None:
                    changes.append(str(item).strip())
        elif isinstance(raw_changes, str) and raw_changes.strip():
            changes.append(raw_changes.strip())

        raw_rule_ids = data.get("triggered_rule_ids", [])
        triggered_rule_ids: list[int] = []
        if isinstance(raw_rule_ids, list):
            for item in raw_rule_ids:
                try:
                    rid = int(item)
                    if 0 <= rid < n_rules and rid not in triggered_rule_ids:
                        triggered_rule_ids.append(rid)
                except (ValueError, TypeError):
                    continue

        return ChangeReport(
            changes=changes,
            triggered_rule_ids=triggered_rule_ids,
            raw=raw,
            parse_error=False,
        )
    except Exception:
        return ChangeReport(raw=raw, parse_error=True)
