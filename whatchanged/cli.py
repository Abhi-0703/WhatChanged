"""Headless command-line runner and replay tool for What Changed?."""

import argparse
from pathlib import Path
import sys
import time

from whatchanged.backends import get_backend
from whatchanged.config import Settings
from whatchanged.engine import Watcher
from whatchanged.sources import open_source
from whatchanged.store import EventStore, export_markdown


def main():
    parser = argparse.ArgumentParser(
        description="What Changed? — Headless visual change watcher and replay tool"
    )
    parser.add_argument(
        "--source",
        default="0",
        help="Frame source specifier: webcam index (0), phone URL, video file, or folder path",
    )
    parser.add_argument(
        "--backend",
        default="ollama",
        choices=["ollama", "gemini", "fake"],
        help="Model inference backend",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=1.0,
        help="Seconds between tick steps",
    )
    parser.add_argument(
        "--max-ticks",
        type=int,
        default=0,
        help="Maximum tick iterations before exiting (0 for continuous loop)",
    )
    parser.add_argument(
        "--rule",
        action="append",
        dest="rules",
        help="Alert rule string (can be specified multiple times)",
    )
    parser.add_argument(
        "--export",
        type=str,
        default="",
        help="Path to export markdown timeline on exit",
    )
    args = parser.parse_args()

    settings = Settings.from_env()
    settings.backend = args.backend
    settings.interval = args.interval

    rules = args.rules or settings.default_rules

    print("==================================================")
    print("      What Changed? — Visual Change Watcher       ")
    print("==================================================")
    print(f"Source:        {args.source}")
    print(f"Backend:       {args.backend}")
    print(f"Interval:      {args.interval}s")
    print(f"Active Rules:  {rules}")
    print("--------------------------------------------------")

    try:
        source = open_source(args.source)
    except Exception as e:
        print(f"Error opening source '{args.source}': {e}", file=sys.stderr)
        sys.exit(1)

    backend = get_backend(args.backend, settings)
    is_avail, avail_msg = backend.is_available()
    print(f"Backend Status: {avail_msg}")

    store = EventStore()
    watcher = Watcher(source, backend, settings, rules)
    recorded_events = []

    ticks = 0
    try:
        while True:
            ticks += 1
            new_events = watcher.step()

            for ev in new_events:
                recorded_events.append(ev)
                store.append_event(ev)
                print(f"\n[EVENT DETECTED @ {ev.timestamp}]")
                print(f"  Pixel Diff: {ev.diff_percent:.1f}% | Latency: {ev.latency_ms}ms")
                print(f"  Changes:    {', '.join(ev.changes)}")
                if ev.triggered_rules:
                    print(f"  🚨 RULES TRIGGERED: {', '.join(ev.triggered_rules)}")

            stats = watcher.stats()
            sys.stdout.write(
                f"\rTick #{ticks} | Status: {stats['status']:<9} | "
                f"Frames: {stats['frames_seen']} | Skipped: {stats['skipped']} ({stats['calls_saved_percent']}%) | "
                f"Model Calls: {stats['model_calls']}   "
            )
            sys.stdout.flush()

            if args.max_ticks > 0 and ticks >= args.max_ticks:
                break

            time.sleep(args.interval)

    except KeyboardInterrupt:
        print("\n\nWatcher interrupted by user.")
    finally:
        watcher.close()
        print("\n--------------------------------------------------")
        stats = watcher.stats()
        print(f"Session finished:")
        print(f"  Total frames checked:   {stats['frames_seen']}")
        print(f"  Frames skipped (no AI): {stats['skipped']} ({stats['calls_saved_percent']}%)")
        print(f"  Total model calls:      {stats['model_calls']}")
        print(f"  Events recorded:        {len(recorded_events)}")

        if args.export:
            md = export_markdown(recorded_events)
            Path(args.export).write_text(md, encoding="utf-8")
            print(f"  Timeline exported to:   {args.export}")


if __name__ == "__main__":
    main()
