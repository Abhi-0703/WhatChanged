"""Prompt templates for What Changed? vision models."""

from typing import List


def build_prompt(rules: list[str], mode: str = "side_by_side") -> str:
    """Builds a strict structured prompt directing Gemma 4 to analyze visual changes."""
    rules_block = ""
    if rules:
        rules_lines = [f"  {idx}: {rule}" for idx, rule in enumerate(rules)]
        rules_block = (
            "\nUSER ALERT RULES (check each rule index against observed changes):\n"
            + "\n".join(rules_lines)
            + "\nIf any of the above rules were triggered by the changes, include its integer index in 'triggered_rule_ids'."
        )
    else:
        rules_block = "\nNo user rules configured. Set 'triggered_rule_ids': []."

    if mode == "side_by_side":
        image_instruction = (
            "You are looking at a single composite image from a fixed security/monitoring camera.\n"
            "- The LEFT half is labelled 'BEFORE' (reference frame).\n"
            "- The RIGHT half is labelled 'AFTER' (current frame)."
        )
    else:
        image_instruction = (
            "You are looking at two sequential images from a fixed camera.\n"
            "- Image 1 is 'BEFORE' (reference frame).\n"
            "- Image 2 is 'AFTER' (current frame)."
        )

    return f"""You are an expert visual change analyzer.
{image_instruction}

TASK:
Identify ONLY real, physical changes between BEFORE and AFTER:
- Objects added to the scene
- Objects removed from the scene
- Objects moved, shifted, or rearranged
- Doors, windows, or drawers opened or closed
- People or pets entering, exiting, or moving

STRICT NEGATIVE CONSTRAINTS:
- Completely IGNORE changes in lighting, illumination, sunlight, shadows, highlights, camera auto-exposure, sensor noise, or video compression artifacts.
- Do NOT hallucinate changes. If nothing physically changed or only lighting changed, report NO changes.
{rules_block}

RESPONSE FORMAT:
You MUST respond with valid, raw JSON only. Do NOT include markdown code fences, greetings, or explanations.
JSON schema:
{{
  "changes": [
    "Brief description of change 1",
    "Brief description of change 2"
  ],
  "triggered_rule_ids": [0]
}}

If no physical changes occurred:
{{
  "changes": [],
  "triggered_rule_ids": []
}}
"""
