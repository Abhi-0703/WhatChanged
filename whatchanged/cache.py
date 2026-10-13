"""Response cache for What Changed?

Provides offline, zero-network instant responses for replay and sample modes,
ensuring demos succeed reliably even without internet or API keys.
"""

import hashlib
import json
from pathlib import Path
from typing import Optional
import cv2
from whatchanged.imaging import to_jpeg_bytes
from whatchanged.report import ChangeReport


class ResponseCache:
    """Stores and retrieves cached model inferences by frame content hash."""

    def __init__(self, cache_dir: str | Path = ".cache") -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_file = self.cache_dir / "responses.json"
        self._memory_cache: dict[str, dict] = {}
        self._load_cache()
        self._seed_sample_cache()

    def _hash_pair(self, before_bytes: bytes, after_bytes: bytes) -> str:
        """Computes deterministic hash from the before and after image bytes."""
        h = hashlib.sha256()
        h.update(before_bytes)
        h.update(b"__SEP__")
        h.update(after_bytes)
        return h.hexdigest()

    def _load_cache(self) -> None:
        if self.cache_file.exists():
            try:
                self._memory_cache = json.loads(self.cache_file.read_text(encoding="utf-8"))
            except Exception:
                self._memory_cache = {}

    def _save_cache(self) -> None:
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            self.cache_file.write_text(json.dumps(self._memory_cache, indent=2), encoding="utf-8")
        except Exception:
            pass

    def _seed_sample_cache(self) -> None:
        """Seeds offline responses for the pre-rendered sample demo frames."""
        samples_dir = Path("samples")
        if not samples_dir.exists():
            return

        def load_encoded(name: str) -> bytes:
            p = samples_dir / name
            if not p.exists():
                return b""
            try:
                frame = cv2.imread(str(p))
                if frame is not None:
                    return to_jpeg_bytes(frame, max_side=768, quality=85)
            except Exception:
                pass
            return b""

        s1 = load_encoded("01_empty_desk.jpg")
        s2 = load_encoded("02_bottle_added.jpg")
        s3 = load_encoded("03_bottle_moved.jpg")
        s4 = load_encoded("04_notebook_added.jpg")
        s5 = load_encoded("05_bottle_removed.jpg")

        seed_pairs = [
            (s1, s2, ["Water bottle placed on the right side of the desk"], [0]),
            (s2, s3, ["Water bottle moved from right side to left side of desk"], [0]),
            (s3, s4, ["Green notebook placed on the center of the desk"], []),
            (s4, s5, ["Water bottle removed from the desk"], []),
            (s5, s1, ["Green notebook removed, restoring empty desk"], []),
        ]

        for before_b, after_b, changes, rule_ids in seed_pairs:
            if before_b and after_b:
                k = self._hash_pair(before_b, after_b)
                self._memory_cache[k] = {
                    "changes": changes,
                    "triggered_rule_ids": rule_ids,
                    "raw": "Pre-cached offline demo response",
                }

    def get(self, before_bytes: bytes, after_bytes: bytes, n_rules: int) -> Optional[ChangeReport]:
        """Retrieves a cached ChangeReport if present."""
        if not before_bytes or not after_bytes:
            return None

        k = self._hash_pair(before_bytes, after_bytes)
        data = self._memory_cache.get(k)
        if data:
            valid_rules = [
                rid for rid in data.get("triggered_rule_ids", [])
                if 0 <= rid < n_rules
            ]
            return ChangeReport(
                changes=list(data.get("changes", [])),
                triggered_rule_ids=list(valid_rules),
                raw=data.get("raw", "Cached response"),
                parse_error=False,
                rate_limited=False,
            )
        return None

    def put(self, before_bytes: bytes, after_bytes: bytes, report: ChangeReport) -> None:
        """Stores a successful ChangeReport in the cache."""
        if not before_bytes or not after_bytes or report.parse_error or report.rate_limited:
            return

        k = self._hash_pair(before_bytes, after_bytes)
        self._memory_cache[k] = {
            "changes": report.changes,
            "triggered_rule_ids": report.triggered_rule_ids,
            "raw": report.raw,
        }
        self._save_cache()


# Global default cache instance
default_cache = ResponseCache()
