"""Gemini API backend for What Changed?."""

import time
from typing import List, Tuple
from google import genai
from google.genai import types
import numpy as np

from whatchanged.backends.base import Backend
from whatchanged.config import Settings
from whatchanged.imaging import side_by_side, to_jpeg_bytes
from whatchanged.prompts import build_prompt
from whatchanged.report import ChangeReport, parse_report


class GeminiBackend(Backend):
    """Cloud fallback backend using Google Gemini API and Gemma / Gemini models."""

    def __init__(self, settings: Settings) -> None:
        self.api_key = settings.gemini_api_key
        self.model = settings.gemini_model
        self.image_mode = settings.image_mode
        self.max_side = settings.max_side
        self.quality = settings.jpeg_quality
        self._client: genai.Client | None = None
        if self.api_key:
            self._client = genai.Client(api_key=self.api_key)

    @property
    def name(self) -> str:
        return f"Gemini API ({self.model})"

    def is_available(self) -> Tuple[bool, str]:
        if not self.api_key:
            return False, "GEMINI_API_KEY is not set. Enter an API key in .env or the UI."
        return True, f"Gemini API configured with model '{self.model}'."

    def describe_change(
        self,
        before: np.ndarray,
        after: np.ndarray,
        rules: list[str],
    ) -> ChangeReport:
        if not self.api_key or self._client is None:
            return ChangeReport(
                changes=[],
                triggered_rule_ids=[],
                raw="GEMINI_API_KEY is not configured.",
                parse_error=True,
            )

        prompt = build_prompt(rules, mode=self.image_mode)

        contents: list = [prompt]
        if self.image_mode == "side_by_side":
            stitched = side_by_side(before, after)
            img_bytes = to_jpeg_bytes(stitched, max_side=self.max_side, quality=self.quality)
            contents.append(types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg"))
        else:
            b_bytes = to_jpeg_bytes(before, max_side=self.max_side, quality=self.quality)
            a_bytes = to_jpeg_bytes(after, max_side=self.max_side, quality=self.quality)
            contents.append(types.Part.from_bytes(data=b_bytes, mime_type="image/jpeg"))
            contents.append(types.Part.from_bytes(data=a_bytes, mime_type="image/jpeg"))

        last_error = ""
        for attempt in range(2):
            try:
                response = self._client.models.generate_content(
                    model=self.model,
                    contents=contents,
                )
                raw_text = response.text or ""
                report = parse_report(raw_text, len(rules))
                if not report.parse_error:
                    return report
                last_error = f"Parse error in model response: {raw_text[:120]}"
            except Exception as e:
                last_error = str(e)

            if attempt == 0:
                time.sleep(1.0)

        return ChangeReport(
            changes=[],
            triggered_rule_ids=[],
            raw=last_error,
            parse_error=True,
        )
