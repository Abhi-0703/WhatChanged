"""Unit tests for Watcher engine with FakeBackend and mock frame sources."""

import time
import numpy as np
import pytest

from whatchanged.backends import FakeBackend
from whatchanged.config import Settings
from whatchanged.engine import Watcher
from whatchanged.sources import FrameSource
from whatchanged.store import EventStore, export_markdown


class MockListSource(FrameSource):
    """Feeds a predetermined sequence of numpy frames."""

    def __init__(self, frames: list[np.ndarray]) -> None:
        self.frames = frames
        self.index = 0

    def read(self) -> np.ndarray | None:
        if self.index < len(self.frames):
            frame = self.frames[self.index]
            self.index += 1
            return frame
        # If exhausted, return the last frame
        return self.frames[-1] if self.frames else None


def _make_frame(val: int) -> np.ndarray:
    return np.full((120, 160, 3), val, dtype=np.uint8)


def _make_frame_with_rect(val: int, rect_val: int) -> np.ndarray:
    f = _make_frame(val)
    f[30:90, 40:120] = rect_val
    return f


def test_static_frames_no_model_calls():
    # 5 identical frames
    f = _make_frame(100)
    source = MockListSource([f, f, f, f, f])
    backend = FakeBackend()
    settings = Settings(sensitivity=2.0)
    watcher = Watcher(source, backend, settings)

    for _ in range(5):
        watcher.step()

    stats = watcher.stats()
    assert stats["model_calls"] == 0
    assert stats["skipped"] == 4  # First establishes reference, next 4 skipped
    assert stats["calls_saved_percent"] == 80.0
    watcher.close()


def test_one_real_change_settles_and_fires_event():
    f0 = _make_frame(50)
    # Changed frame (has white rectangle)
    f_change = _make_frame_with_rect(50, 255)

    # Frame sequence:
    # 0: reference
    # 1: change detected -> becomes candidate (settling)
    # 2: same changed frame -> scene settled! Triggers model call
    # 3: model future finishes -> event harvested!
    source = MockListSource([f0, f_change, f_change, f_change])
    backend = FakeBackend(canned_changes=["Cup placed on desk"], canned_rule_ids=[0])
    settings = Settings(sensitivity=2.0)
    rules = ["alert when cup is placed"]
    watcher = Watcher(source, backend, settings, rules=rules)

    all_events = []
    # Step 0: reference established
    ev0 = watcher.step()
    assert len(ev0) == 0

    # Step 1: candidate stored (settling)
    ev1 = watcher.step()
    assert len(ev1) == 0
    assert watcher.status == "Settling"

    # Step 2: settled! job submitted
    ev2 = watcher.step()
    assert watcher.model_calls == 1

    # Wait for the async worker future to finish
    time.sleep(0.05)

    # Step 3: job harvested, event returned
    ev3 = watcher.step()
    all_events.extend(ev3)

    assert len(all_events) == 1
    event = all_events[0]
    assert event.changes == ["Cup placed on desk"]
    assert event.triggered_rules == ["alert when cup is placed"]
    assert event.diff_percent > 5.0
    assert event.before_bytes != b""
    assert event.after_bytes != b""

    watcher.close()


def test_continuous_motion_delays_model_call():
    f0 = _make_frame(50)
    # Successive distinct changes (motion in progress)
    f_move1 = _make_frame_with_rect(50, 180)
    f_move2 = _make_frame_with_rect(50, 220)
    f_settled = _make_frame_with_rect(50, 255)

    # Sequence: ref, move1 (candidate), move2 (replaces candidate), settled (replaces), settled (stable -> fire)
    source = MockListSource([f0, f_move1, f_move2, f_settled, f_settled, f_settled])
    backend = FakeBackend()
    settings = Settings(sensitivity=2.0)
    watcher = Watcher(source, backend, settings)

    # Tick 0: ref
    watcher.step()
    assert watcher.model_calls == 0

    # Tick 1: move1 -> candidate
    watcher.step()
    assert watcher.model_calls == 0
    assert watcher.status == "Settling"

    # Tick 2: move2 -> replaces candidate (still settling)
    watcher.step()
    assert watcher.model_calls == 0
    assert watcher.status == "Settling"

    # Tick 3: settled -> replaces candidate (still settling)
    watcher.step()
    assert watcher.model_calls == 0

    # Tick 4: settled again -> difference is 0 -> scene stable -> job submitted!
    watcher.step()
    assert watcher.model_calls == 1

    watcher.close()


def test_budget_guard_caps_calls():
    f0 = _make_frame(50)
    f1 = _make_frame_with_rect(50, 255)
    f2 = _make_frame_with_rect(50, 10)

    # Allow at most 1 call per minute
    settings = Settings(sensitivity=2.0, max_calls_per_min=1)
    backend = FakeBackend()
    # Provide repeated frames so first change settles and second change tries to settle
    source = MockListSource([f0, f1, f1, f1, f2, f2, f2])
    watcher = Watcher(source, backend, settings)

    # Process first change
    watcher.step()  # ref
    watcher.step()  # cand f1
    watcher.step()  # settles -> submits call 1
    assert watcher.model_calls == 1
    time.sleep(0.05)
    watcher.step()  # harvests call 1, sets ref = f1

    # Second change (f2 vs ref f1)
    watcher.step()  # cand f2
    watcher.step()  # f2 settled, but budget guard blocks it!
    assert watcher.model_calls == 1  # Still 1, capped by max_calls_per_min

    watcher.close()


def test_backend_exception_increments_errors_and_continues():
    f0 = _make_frame(50)
    f1 = _make_frame_with_rect(50, 255)

    source = MockListSource([f0, f1, f1, f1])
    backend = FakeBackend(should_raise=True)
    settings = Settings(sensitivity=2.0)
    watcher = Watcher(source, backend, settings)

    watcher.step()  # ref
    watcher.step()  # candidate
    watcher.step()  # submits job
    time.sleep(0.05)
    watcher.step()  # harvests error

    assert watcher.errors >= 1
    # Loop continues operating
    stats = watcher.stats()
    assert stats["errors"] >= 1
    watcher.close()


def test_store_and_export_markdown(tmp_path):
    store = EventStore(base_dir=tmp_path)
    backend = FakeBackend(canned_changes=["Door opened"], canned_rule_ids=[0])
    settings = Settings(sensitivity=2.0)
    f0 = _make_frame(50)
    f1 = _make_frame_with_rect(50, 255)
    source = MockListSource([f0, f1, f1, f1])
    watcher = Watcher(source, backend, settings, rules=["notify if door opened"])

    watcher.step()
    watcher.step()
    watcher.step()
    time.sleep(0.05)
    events = watcher.step()

    assert len(events) == 1
    store.append_event(events[0])

    loaded = store.load_events()
    assert len(loaded) == 1
    assert loaded[0].changes == ["Door opened"]
    assert loaded[0].triggered_rules == ["notify if door opened"]

    md = export_markdown(loaded)
    assert "Door opened" in md
    assert "notify if door opened" in md
    watcher.close()
