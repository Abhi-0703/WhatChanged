"""Core Watcher engine for What Changed?

Orchestrates non-blocking frame capture, cheap OpenCV change detection,
settle step, budget guard, and background model inference.
"""

from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime
import time
from typing import List, Optional, Tuple
import uuid
import numpy as np

from whatchanged.backends.base import Backend
from whatchanged.cache import default_cache
from whatchanged.config import Settings
from whatchanged.detect import change_score
from whatchanged.imaging import to_jpeg_bytes
from whatchanged.report import ChangeReport
from whatchanged.sources import FrameSource
from whatchanged.store import Event


class Watcher:
    """Continuous visual change watcher loop controller."""

    def __init__(
        self,
        source: FrameSource,
        backend: Backend,
        settings: Settings,
        rules: Optional[list[str]] = None,
    ) -> None:
        self.source = source
        self.backend = backend
        self.settings = settings
        self.rules: list[str] = list(rules) if rules is not None else list(settings.default_rules)

        self.reference: Optional[np.ndarray] = None
        self.candidate: Optional[np.ndarray] = None
        self.last_frame: Optional[np.ndarray] = None
        self.candidate_for_job: Optional[np.ndarray] = None

        self.executor = ThreadPoolExecutor(max_workers=1)
        self.pending_future: Optional[Future] = None

        self.recent_call_times: list[float] = []

        # Metrics and counters
        self.frames_seen: int = 0
        self.skipped: int = 0
        self.model_calls: int = 0
        self.errors: int = 0
        self.last_latency_ms: int = 0
        self.last_score: float = 0.0
        self.status: str = "Watching"  # Watching, Settling, Analyzing, Rate Limited, Error, Stopped
        self.rate_limited_until: float = 0.0

    def reset_reference(self) -> None:
        """Forces the next captured frame to become the new reference."""
        self.reference = None
        self.candidate = None
        self.status = "Watching"

    def update_rules(self, rules: list[str]) -> None:
        """Updates the active alert rules evaluated by Gemma 4."""
        self.rules = list(rules)

    def stats(self) -> dict:
        """Returns runtime performance and budget savings metrics."""
        saved_pct = (self.skipped / self.frames_seen * 100.0) if self.frames_seen > 0 else 100.0
        return {
            "frames_seen": self.frames_seen,
            "skipped": self.skipped,
            "model_calls": self.model_calls,
            "errors": self.errors,
            "last_latency_ms": self.last_latency_ms,
            "last_score": round(self.last_score, 2),
            "calls_saved_percent": round(saved_pct, 1),
            "status": self.status,
            "backend_name": self.backend.name,
        }

    def step(self) -> list[Event]:
        """Executes a single non-blocking tick of the watcher loop."""
        new_events: list[Event] = []

        # 1. Harvest finished background model job if pending
        if self.pending_future is not None:
            if self.pending_future.done():
                try:
                    report, lat_ms, diff_val, ref_img, cand_img = self.pending_future.result()
                    self.last_latency_ms = lat_ms

                    if report.rate_limited:
                        self.status = "Rate Limited"
                        self.rate_limited_until = time.time() + 15.0
                    elif report.parse_error:
                        self.errors += 1
                        self.status = "Error"
                    else:
                        self.status = "Watching"
                        if report.changes:
                            matched_rules = [
                                self.rules[rid]
                                for rid in report.triggered_rule_ids
                                if 0 <= rid < len(self.rules)
                            ]

                            event_id = str(uuid.uuid4())[:8]
                            now_str = datetime.now().strftime("%H:%M:%S")

                            ev = Event(
                                id=event_id,
                                timestamp=now_str,
                                timestamp_epoch=time.time(),
                                changes=report.changes,
                                triggered_rules=matched_rules,
                                diff_percent=diff_val,
                                latency_ms=lat_ms,
                                backend_name=self.backend.name,
                                before_bytes=to_jpeg_bytes(ref_img, max_side=self.settings.max_side),
                                after_bytes=to_jpeg_bytes(cand_img, max_side=self.settings.max_side),
                            )
                            new_events.append(ev)

                        # Update reference frame to the settled candidate
                        self.reference = cand_img
                except Exception:
                    self.errors += 1
                    self.status = "Error"
                finally:
                    self.pending_future = None
                    self.candidate_for_job = None
            else:
                self.status = "Analyzing"
                # Keep camera frame buffer drained and live view fresh
                live_f = self.source.read()
                if live_f is not None:
                    self.last_frame = live_f
                return new_events

        # Check if currently cooling down from a 429 rate limit
        if time.time() < self.rate_limited_until:
            self.status = "Rate Limited"
            live_f = self.source.read()
            if live_f is not None:
                self.last_frame = live_f
            return new_events

        # 2. Read current frame
        frame = self.source.read()
        if frame is None or frame.size == 0:
            self.errors += 1
            self.status = "Error"
            return new_events

        self.last_frame = frame
        self.frames_seen += 1

        # 3. Establish initial reference frame
        if self.reference is None:
            self.reference = frame.copy()
            self.status = "Watching"
            return new_events

        # 4. Compute cheap difference score against reference
        score = change_score(self.reference, frame)
        self.last_score = score
        threshold = self.settings.sensitivity

        # 5. Filter frames below threshold
        if score < threshold:
            self.skipped += 1
            self.candidate = None
            self.status = "Watching"
            return new_events

        # 6. Settle step: wait for motion to conclude before triggering model
        if self.candidate is None:
            self.candidate = frame.copy()
            self.status = "Settling"
            return new_events

        # Check if the scene has stabilized between candidate and current frame
        settle_score = change_score(self.candidate, frame)
        if settle_score >= threshold:
            # Motion continues: refresh candidate to latest frame
            self.candidate = frame.copy()
            self.status = "Settling"
            return new_events

        # 7. Check offline/pre-computed response cache before network or model calls
        ref_for_job = self.reference.copy()
        cand_for_job = self.candidate.copy()
        ref_bytes = to_jpeg_bytes(ref_for_job, max_side=self.settings.max_side, quality=self.settings.jpeg_quality)
        cand_bytes = to_jpeg_bytes(cand_for_job, max_side=self.settings.max_side, quality=self.settings.jpeg_quality)

        if self.settings.use_cache:
            cached_report = default_cache.get(ref_bytes, cand_bytes, len(self.rules))
            if cached_report is not None:
                self.last_latency_ms = 0
                self.status = "Watching"
                self.candidate = None
                if cached_report.changes:
                    matched_rules = [
                        self.rules[rid]
                        for rid in cached_report.triggered_rule_ids
                        if 0 <= rid < len(self.rules)
                    ]
                    ev = Event(
                        id=str(uuid.uuid4())[:8],
                        timestamp=datetime.now().strftime("%H:%M:%S"),
                        timestamp_epoch=time.time(),
                        changes=cached_report.changes,
                        triggered_rules=matched_rules,
                        diff_percent=score,
                        latency_ms=0,
                        backend_name=f"{self.backend.name} (Cached)",
                        before_bytes=ref_bytes,
                        after_bytes=cand_bytes,
                    )
                    new_events.append(ev)
                self.reference = cand_for_job
                return new_events

        # 8. Budget guard: cap model calls within sliding 60s window
        now = time.time()
        self.recent_call_times = [t for t in self.recent_call_times if now - t < 60.0]
        if len(self.recent_call_times) >= self.settings.max_calls_per_min:
            # Over budget: keep candidate and wait for next tick
            self.status = "Settling"
            return new_events

        # 9. Submit async inference job
        self.recent_call_times.append(now)
        self.model_calls += 1
        self.status = "Analyzing"

        self.candidate_for_job = cand_for_job
        self.candidate = None

        def _inference_worker(ref, cand, rules, backend, diff_p, r_bytes, c_bytes):
            t0 = time.time()
            rep = backend.describe_change(ref, cand, rules)
            lat = int((time.time() - t0) * 1000)
            if self.settings.use_cache and not rep.parse_error and not rep.rate_limited:
                default_cache.put(r_bytes, c_bytes, rep)
            return rep, lat, diff_p, ref, cand

        self.pending_future = self.executor.submit(
            _inference_worker,
            ref_for_job,
            cand_for_job,
            list(self.rules),
            self.backend,
            score,
            ref_bytes,
            cand_bytes,
        )

        return new_events

    def close(self) -> None:
        """Releases executor and underlying source resources."""
        self.executor.shutdown(wait=False)
        try:
            self.source.close()
        except Exception:
            pass
        self.status = "Stopped"
