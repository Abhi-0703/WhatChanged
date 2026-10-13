"""Event storage and Markdown export for What Changed?."""

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import time
from typing import List, Optional


@dataclass
class Event:
    """A detected physical change event recorded on the timeline."""

    id: str
    timestamp: str  # Human-readable ISO string
    timestamp_epoch: float
    changes: list[str]
    triggered_rules: list[str]
    diff_percent: float
    latency_ms: int
    backend_name: str
    before_bytes: bytes = b""
    after_bytes: bytes = b""


class EventStore:
    """Persists events to JSONL and before/after JPEG files on disk."""

    def __init__(self, base_dir: str | Path = "events") -> None:
        self.base_dir = Path(base_dir)
        self.img_dir = self.base_dir / "img"
        self.jsonl_file = self.base_dir / "events.jsonl"
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        self.img_dir.mkdir(parents=True, exist_ok=True)

    def append_event(self, event: Event) -> None:
        """Saves event images and metadata line."""
        self._ensure_dirs()

        # Save image files
        before_path = self.img_dir / f"{event.id}_before.jpg"
        after_path = self.img_dir / f"{event.id}_after.jpg"

        if event.before_bytes:
            before_path.write_bytes(event.before_bytes)
        if event.after_bytes:
            after_path.write_bytes(event.after_bytes)

        # Build serializable record
        record = {
            "id": event.id,
            "timestamp": event.timestamp,
            "timestamp_epoch": event.timestamp_epoch,
            "changes": event.changes,
            "triggered_rules": event.triggered_rules,
            "diff_percent": round(event.diff_percent, 2),
            "latency_ms": event.latency_ms,
            "backend_name": event.backend_name,
            "before_img": str(before_path.relative_to(self.base_dir)),
            "after_img": str(after_path.relative_to(self.base_dir)),
        }

        with open(self.jsonl_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

    def load_events(self) -> list[Event]:
        """Loads events from disk with their before/after images."""
        if not self.jsonl_file.exists():
            return []

        events: list[Event] = []
        try:
            with open(self.jsonl_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    data = json.loads(line)
                    before_path = self.base_dir / data.get("before_img", "")
                    after_path = self.base_dir / data.get("after_img", "")

                    before_bytes = before_path.read_bytes() if before_path.exists() else b""
                    after_bytes = after_path.read_bytes() if after_path.exists() else b""

                    events.append(
                        Event(
                            id=data["id"],
                            timestamp=data["timestamp"],
                            timestamp_epoch=data.get("timestamp_epoch", 0.0),
                            changes=data.get("changes", []),
                            triggered_rules=data.get("triggered_rules", []),
                            diff_percent=data.get("diff_percent", 0.0),
                            latency_ms=data.get("latency_ms", 0),
                            backend_name=data.get("backend_name", "Unknown"),
                            before_bytes=before_bytes,
                            after_bytes=after_bytes,
                        )
                    )
        except Exception:
            pass
        return events


def export_markdown(events: list[Event]) -> str:
    """Renders events as a structured, human-readable Markdown timeline document."""
    if not events:
        return "# What Changed? — Timeline Report\n\n*No events recorded in this session.*"

    lines = [
        "# What Changed? — Visual Timeline Report",
        f"*Generated on {time.strftime('%Y-%m-%d %H:%M:%S')}*",
        f"*Total Events: {len(events)}*",
        "",
        "---",
        "",
    ]

    for idx, ev in enumerate(reversed(events), 1):
        lines.append(f"### Event #{idx}: {ev.timestamp}")
        lines.append(f"- **Backend:** `{ev.backend_name}` ({ev.latency_ms} ms)")
        lines.append(f"- **Pixel Diff:** `{ev.diff_percent:.1f}%`")
        if ev.triggered_rules:
            rules_str = ", ".join(f"`{r}`" for r in ev.triggered_rules)
            lines.append(f"- **🚨 Rules Triggered:** {rules_str}")
        lines.append("- **Observed Changes:**")
        for ch in ev.changes:
            lines.append(f"  - {ch}")
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)
