"""What Changed? — Streamlit Dashboard

A continuous visual change watcher that stays silent until something changes,
then uses Gemma 4 to explain what changed, logs events on a timeline, and fires
alerts for user-defined rules.
"""

from datetime import datetime
from pathlib import Path
import time
import cv2
import numpy as np
import streamlit as st

from whatchanged.backends import get_backend
from whatchanged.config import Settings
from whatchanged.engine import Watcher
from whatchanged.imaging import to_jpeg_bytes
from whatchanged.sources import open_source
from whatchanged.store import Event, EventStore, export_markdown

# Page configuration
st.set_page_config(
    page_title="What Changed? — Visual Change Watcher",
    page_icon="👁️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom styling for badges, metrics, and alert banners
st.markdown(
    """
    <style>
    .status-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 16px;
        font-weight: 600;
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .status-watching { background-color: #e0f2fe; color: #0369a1; border: 1px solid #bae6fd; }
    .status-settling { background-color: #fef3c7; color: #b45309; border: 1px solid #fde68a; }
    .status-analyzing { background-color: #f3e8ff; color: #7e22ce; border: 1px solid #e9d5ff; }
    .status-ratelimited { background-color: #fef9c3; color: #a16207; border: 1px solid #fde047; }
    .status-stopped { background-color: #f1f5f9; color: #475569; border: 1px solid #cbd5e1; }
    .status-error { background-color: #fee2e2; color: #b91c1c; border: 1px solid #fecaca; }
    .alert-banner {
        background: linear-gradient(90deg, #991b1b, #dc2626);
        color: white;
        padding: 14px 18px;
        border-radius: 8px;
        font-size: 1.05rem;
        font-weight: 600;
        margin-bottom: 15px;
        box-shadow: 0 4px 12px rgba(220, 38, 38, 0.25);
    }
    .headline-metric {
        font-size: 2.2rem;
        font-weight: 700;
        color: #059669;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Initialize Session State
if "store" not in st.session_state:
    st.session_state.store = EventStore()
if "events" not in st.session_state:
    st.session_state.events = st.session_state.store.load_events()
if "watcher" not in st.session_state:
    st.session_state.watcher = None
if "is_running" not in st.session_state:
    st.session_state.is_running = False
if "latest_alert" not in st.session_state:
    st.session_state.latest_alert = None
if "alert_timestamp" not in st.session_state:
    st.session_state.alert_timestamp = 0.0
if "snapshot_notice" not in st.session_state:
    st.session_state.snapshot_notice = None

# --- SIDEBAR CONFIGURATION ---
st.sidebar.title("👁️ What Changed?")
st.sidebar.caption("Visual Change Watcher — Hosted Gemma 4 (Gemini API) + Local Gemma 4 (Ollama)")

# Source selector
source_spec = st.sidebar.text_input(
    "Frame Source",
    value="0",
    help="Webcam index ('0', '1'), phone stream ('http://192.168.1.X:8080/video'), video file, or folder of images ('samples/').",
)

# Backend selection: Gemini API is now default
backend_choice = st.sidebar.radio(
    "Inference Backend",
    options=["Gemini API (Hosted Gemma 4)", "Local Ollama (On-Device Gemma 4)", "Fake Backend (Offline Simulation)"],
    index=0,
    help="Hosted Gemma 4 via Gemini API for convenience; local Gemma 4 via Ollama for privacy & offline use.",
)

backend_key = "gemini"
if "Ollama" in backend_choice:
    backend_key = "ollama"
elif "Fake" in backend_choice:
    backend_key = "fake"

# Model names
settings = Settings.from_env()
if backend_key == "gemini":
    gemini_key = st.sidebar.text_input(
        "Gemini API Key",
        value=settings.gemini_api_key,
        type="password",
        help="Google AI Studio API key.",
    )
    model_name = st.sidebar.text_input("Gemma 4 Model ID", value=settings.gemini_model)
    settings.gemini_api_key = gemini_key
    settings.gemini_model = model_name
elif backend_key == "ollama":
    model_name = st.sidebar.text_input("Ollama Model", value=settings.ollama_model)
    ollama_host = st.sidebar.text_input("Ollama Host", value=settings.ollama_host)
    settings.ollama_model = model_name
    settings.ollama_host = ollama_host

# Rules
rules_text = st.sidebar.text_area(
    "Alert Rules (one per line)",
    value="notify me if the door is opened\nalert if a bag or backpack is left behind\nnotify if a laptop is moved",
    height=100,
)
rules = [r.strip() for r in rules_text.splitlines() if r.strip()]

# Advanced Watcher sliders
with st.sidebar.expander("⚙️ Watcher Tuning", expanded=False):
    interval_s = st.slider("Check Interval (seconds)", min_value=1.0, max_value=30.0, value=3.0, step=0.5)
    sensitivity = st.slider("Sensitivity Threshold (%)", min_value=0.5, max_value=10.0, value=2.0, step=0.1)
    max_calls = st.slider("Budget Guard (Max calls/min)", min_value=1, max_value=20, value=4, step=1)
    image_mode = st.selectbox("Image Mode", options=["side_by_side", "two_images"], index=0)

settings.interval = interval_s
settings.sensitivity = sensitivity
settings.max_calls_per_min = max_calls
settings.image_mode = image_mode

# Control buttons
col_ctrl1, col_ctrl2 = st.sidebar.columns(2)

def start_watcher():
    try:
        source = open_source(source_spec)
    except Exception as e:
        st.sidebar.error(f"Cannot open source '{source_spec}': {e}")
        return

    backend = get_backend(backend_key, settings)
    is_avail, msg = backend.is_available()
    if not is_avail and backend_key != "fake":
        st.sidebar.warning(msg)

    st.session_state.watcher = Watcher(source, backend, settings, rules=rules)
    st.session_state.is_running = True

def stop_watcher():
    if st.session_state.watcher:
        st.session_state.watcher.close()
        st.session_state.watcher = None
    st.session_state.is_running = False

with col_ctrl1:
    if not st.session_state.is_running:
        if st.button("▶️ Start", use_container_width=True, type="primary"):
            start_watcher()
            st.rerun()
    else:
        if st.button("⏹️ Stop", use_container_width=True):
            stop_watcher()
            st.rerun()

with col_ctrl2:
    if st.button("🔄 Reset Ref", use_container_width=True):
        if st.session_state.watcher:
            st.session_state.watcher.reset_reference()
            st.toast("Reference frame reset.")

# Snapshot button for capturing people-free samples
if st.sidebar.button("📸 Save Snapshot to samples/", use_container_width=True):
    samples_dir = Path("samples")
    samples_dir.mkdir(parents=True, exist_ok=True)
    frame_to_save = None
    if st.session_state.watcher and st.session_state.watcher.last_frame is not None:
        frame_to_save = st.session_state.watcher.last_frame
    else:
        # Try capturing a single frame directly
        try:
            with open_source(source_spec) as direct_src:
                frame_to_save = direct_src.read()
        except Exception:
            frame_to_save = None

    if frame_to_save is not None:
        ts_name = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = samples_dir / f"snapshot_{ts_name}.jpg"
        cv2.imwrite(str(out_path), frame_to_save)
        st.session_state.snapshot_notice = f"Saved snapshot to `{out_path}`"
        st.toast(f"Snapshot saved to {out_path.name}")
    else:
        st.sidebar.error("Could not capture frame from current source.")

if st.session_state.snapshot_notice:
    st.sidebar.success(st.session_state.snapshot_notice)

# Check and display backend availability advice in sidebar
current_backend = get_backend(backend_key, settings)
is_avail, avail_msg = current_backend.is_available()
if not is_avail:
    st.sidebar.info(f"💡 **Backend Note:** {avail_msg}")

# --- MAIN CONTENT AREA ---

# Top Header & Headline Metrics
header_col1, header_col2 = st.columns([3, 1])
with header_col1:
    st.title("What Changed?")
    st.caption("A camera that stays quiet until something changes — powered by open-weight Gemma 4.")

# Alert Banner
if st.session_state.latest_alert:
    # Auto-fade alert after 30s or allow dismiss
    if time.time() - st.session_state.alert_timestamp < 30.0:
        alert_col, dismiss_col = st.columns([9, 1])
        with alert_col:
            st.markdown(
                f"<div class='alert-banner'>🚨 <strong>RULE ALERT:</strong> {st.session_state.latest_alert}</div>",
                unsafe_allow_html=True,
            )
        with dismiss_col:
            if st.button("Dismiss", key="dismiss_alert"):
                st.session_state.latest_alert = None
                st.rerun()
    else:
        st.session_state.latest_alert = None

# Metrics calculation
stats = {"frames_seen": 0, "skipped": 0, "calls_saved_percent": 100.0, "model_calls": 0, "last_latency_ms": 0, "status": "Stopped"}
if st.session_state.watcher:
    # Update rules dynamically if changed in UI
    st.session_state.watcher.update_rules(rules)
    stats = st.session_state.watcher.stats()
elif st.session_state.events:
    stats["status"] = "Stopped"

# Metric Cards Row
m_col1, m_col2, m_col3, m_col4, m_col5 = st.columns(5)
with m_col1:
    st.metric("Frames Evaluated", f"{stats['frames_seen']}")
with m_col2:
    st.metric("Frames Skipped", f"{stats['skipped']}")
with m_col3:
    st.metric("Frames Needing No AI (Saved)", f"{stats['calls_saved_percent']}%", delta=f"{stats['calls_saved_percent']}%")
with m_col4:
    st.metric("Gemma 4 Calls", f"{stats['model_calls']}")
with m_col5:
    st.metric("Model Latency", f"{stats['last_latency_ms']} ms", delta=f"{stats['status']}")

st.divider()

# Live Video Feed & Timeline Split
feed_col, timeline_col = st.columns([1, 1])

# Live Feed / Status Panel Fragment
@st.fragment(run_every=f"{max(1.0, interval_s)}s" if st.session_state.is_running else None)
def live_feed_panel():
    st.subheader("Live Camera Monitor")

    status_str = "STOPPED"
    status_class = "status-stopped"
    last_score_str = "0.0%"

    if st.session_state.is_running and st.session_state.watcher:
        # Execute one step of the watcher loop
        new_events = st.session_state.watcher.step()
        for ev in new_events:
            st.session_state.events.insert(0, ev)
            st.session_state.store.append_event(ev)
            if ev.triggered_rules:
                st.session_state.latest_alert = ", ".join(ev.triggered_rules)
                st.session_state.alert_timestamp = time.time()
                st.toast(f"🚨 Rule Alert: {st.session_state.latest_alert}")

        current_stats = st.session_state.watcher.stats()
        status_name = current_stats["status"].upper()
        status_class = f"status-{status_name.lower().replace(' ', '')}"
        if status_name == "RATE LIMITED":
            status_str = "RATE LIMITED (SLOWING DOWN)"
        else:
            status_str = status_name
        last_score_str = f"{current_stats['last_score']}%"

    st.markdown(
        f"Status: <span class='status-badge {status_class}'>{status_str}</span> &nbsp;&nbsp; "
        f"Diff: <code>{last_score_str}</code> (threshold: {sensitivity}%)",
        unsafe_allow_html=True,
    )

    if status_str.startswith("RATE LIMITED"):
        st.warning("⚠️ **Rate limited (HTTP 429)**: The watcher is automatically backing off and slowing down calls to conserve quota.")

    # Show live or reference frame
    display_frame = None
    if st.session_state.watcher and st.session_state.watcher.last_frame is not None:
        display_frame = st.session_state.watcher.last_frame
    elif st.session_state.watcher and st.session_state.watcher.reference is not None:
        display_frame = st.session_state.watcher.reference

    if display_frame is not None:
        rgb_frame = cv2.cvtColor(display_frame, cv2.COLOR_BGR2RGB)
        st.image(rgb_frame, caption=f"Live Feed [{source_spec}]", use_container_width=True)
    else:
        if st.session_state.is_running:
            st.warning(
                f"Connecting to source '{source_spec}'... If using webcam (0), please verify camera permissions in macOS."
            )
        else:
            st.info("Watcher is stopped. Click **▶️ Start** in the sidebar to begin monitoring.")

with feed_col:
    live_feed_panel()

# Event Timeline Panel
with timeline_col:
    t_header_col, dl_col = st.columns([2, 1])
    with t_header_col:
        st.subheader(f"Activity Timeline ({len(st.session_state.events)})")
    with dl_col:
        if st.session_state.events:
            md_doc = export_markdown(st.session_state.events)
            st.download_button(
                "📥 Export (.md)",
                data=md_doc,
                file_name="whatchanged_timeline.md",
                mime="text/markdown",
                use_container_width=True,
            )

    if not st.session_state.events:
        st.info("No changes recorded yet. When a physical change settles, Gemma 4 will describe it here.")
    else:
        # Display latest events with before/after comparative panels
        for ev in st.session_state.events[:15]:
            with st.container(border=True):
                time_col, badge_col = st.columns([2, 2])
                with time_col:
                    st.markdown(f"**⏰ {ev.timestamp}** &nbsp;•&nbsp; `{ev.backend_name}`")
                with badge_col:
                    if ev.triggered_rules:
                        st.markdown(
                            f"<span style='color: #dc2626; font-weight: bold;'>🚨 {ev.triggered_rules[0]}</span>",
                            unsafe_allow_html=True,
                        )
                    else:
                        st.caption(f"Diff: {ev.diff_percent:.1f}% | {ev.latency_ms}ms")

                # Before/After images
                img_c1, img_c2 = st.columns(2)
                with img_c1:
                    if ev.before_bytes:
                        st.image(ev.before_bytes, caption="Before", use_container_width=True)
                with img_c2:
                    if ev.after_bytes:
                        st.image(ev.after_bytes, caption="After", use_container_width=True)

                # Changes bullet list
                st.markdown("**What changed:**")
                for ch in ev.changes:
                    st.markdown(f"- {ch}")
