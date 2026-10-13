"""Ollama local backend for Gemma 4."""

import base64
import time
from typing import List, Tuple
import numpy as np
import ollama

from whatchanged.backends.base import Backend
from whatchanged.config import Settings
from whatchanged.imaging import side_by_side, to_jpeg_bytes
from whatchanged.prompts import build_prompt
from whatchanged.report import ChangeReport, parse_report


class OllamaBackend(Backend):
    """Local inference backend using Ollama and open-weight Gemma 4."""

    def __init__(self, settings: Settings) -> None:
        self.model = settings.ollama_model
        self.host = settings.ollama_host
        self.image_mode = settings.image_mode
        self.max_side = settings.max_side
        self.quality = settings.jpeg_quality
        self.client = ollama.Client(host=self.host)

    @property
    def name(self) -> str:
        return f"Ollama ({self.model})"

    def is_available(self) -> Tuple[bool, str]:
        """Checks if Ollama daemon is reachable and whether the model is pulled."""
        try:
            models_response = self.client.list()
            # models_response can be a dict with 'models' or an object with models
            models_list = []
            if hasattr(models_response, "models"):
                models_list = [m.model for m in models_response.models]
            elif isinstance(models_response, dict):
                models_list = [m.get("name", m.get("model", "")) for m in models_response.get("models", [])]

            # Check if model or tag is in list
            for m in models_list:
                if self.model in m or m.startswith(self.model.split(":")[0]):
                    return True, f"Ollama connected, model '{self.model}' ready."

            return False, f"Ollama is running, but model '{self.model}' is not pulled yet. Run: ollama pull {self.model}"
        except Exception as e:
            return False, f"Ollama is not running at {self.host}. Start it with: ollama serve (or brew services start ollama)"

    def _call_model(self, prompt: str, images_bytes: list[bytes]) -> str:
        # Encode images as base64 strings or pass raw bytes
        images_payload = [base64.b64encode(b).decode("utf-8") for b in images_bytes]

        messages = [
            {
                "role": "user",
                "content": prompt,
                "images": images_payload,
            }
        ]

        response = self.client.chat(
            model=self.model,
            messages=messages,
            format="json",
            options={"temperature": 0.0},
        )

        if hasattr(response, "message"):
            return response.message.content or ""
        elif isinstance(response, dict):
            return response.get("message", {}).get("content", "")
        return str(response)

    def describe_change(
        self,
        before: np.ndarray,
        after: np.ndarray,
        rules: list[str],
    ) -> ChangeReport:
        """Runs change detection inference through local Gemma 4 with 1 automatic retry."""
        prompt = build_prompt(rules, mode=self.image_mode)

        if self.image_mode == "side_by_side":
            stitched = side_by_side(before, after)
            img_bytes = [to_jpeg_bytes(stitched, max_side=self.max_side, quality=self.quality)]
        else:
            b_bytes = to_jpeg_bytes(before, max_side=self.max_side, quality=self.quality)
            a_bytes = to_jpeg_bytes(after, max_side=self.max_side, quality=self.quality)
            img_bytes = [b_bytes, a_bytes]

        last_error = ""
        # 1 retry with 1s backoff on transient errors or parse errors
        for attempt in range(2):
            try:
                raw_text = self._call_model(prompt, img_bytes)
                report = parse_report(raw_text, len(rules))
                if not report.parse_error:
                    return report
                # If parse error, retry once
                last_error = f"Parse error in model response: {raw_text[:120]}"
            except Exception as e:
                last_error = str(e)

            if attempt == 0:
                time.sleep(1.0)

        # Fallback error report if all retries fail
        return ChangeReport(
            changes=[],
            triggered_rule_ids=[],
            raw=last_error,
            parse_error=True,
        )
