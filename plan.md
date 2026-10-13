# plan.md — "What Changed?" Open-Source Visual Change Watcher

> **Hackathon:** C³ × Hacktoberfest Hack Day (Hack Day Pune × Cloud Computing Club)
> **Challenge:** Best Open-Source AI Project + Best Use of Gemma 4
> **Build window:** ~2 hours of coding + ~30 min for docs and demo prep
> **Audience for this file:** an AI coding agent (Claude Code, Cursor, Codex, etc.) working with a human teammate.

---

## 0. Kickoff prompt (human: paste this to the agent first)

```
Read plan.md completely before doing anything. Execute it phase by phase, in order.
After each phase: run the acceptance checks, commit with the given message, then tell me
what you did in 3 lines and continue. Do not skip phases. Do not add features that are not in
the plan. Never commit secrets. If something is ambiguous, pick the simplest option, note it
in NOTES.md, and keep going. Ask me only if you are blocked.
```

## 1. Agent operating rules (non-negotiable)

1. **Start from an empty repo created today.** The event requires an original project with meaningful technical contributions made during the Hack Day. Do not paste in code written before the event.
2. **Commit early and often** (at least once per phase, ideally per task) with clear messages. The git history is evidence of work done during the event.
3. **Never commit secrets.** API keys live only in `.env` (gitignored). Only `.env.example` is committed. The repo will be public.
4. **Never commit personal images** (faces, ID cards, room photos with people). Only commit sample frames that contain no people.
5. **Open-weight AI is the core, not decoration.** The project must run fully locally with Gemma 4 through Ollama, and optionally through the Gemini API. Both backends are first-class.
6. **Keep it small.** Python only. No database server, no Docker, no front-end framework. Prefer the standard library plus the listed dependencies.
7. **Verify, don't assume.** Model IDs, SDK method names and Ollama flags change. Check them against current docs, the installed packages, or the installed skills (section 5) before relying on them.
8. **Every phase has acceptance checks.** Do not move on until they pass.
9. **Time-box.** If a task exceeds its budget by 2x, use the simplest fallback listed and move on.
10. **Disclose AI assistance.** Add a short "Built with AI assistance" note in the README (check the organizers' rules on AI-assisted coding). The human teammates must be able to explain every module in the demo.

---

## 2. Hackathon requirements → how this plan satisfies them

| Requirement from the participant guidelines | Where it is handled |
|---|---|
| Original project, meaningful technical contributions during the event | Rule 1 and 2, fresh repo in Phase 1, frequent commits |
| Open-source / open-weight AI must be an important part | Gemma 4 is the only vision-language model used; local Ollama backend (Phase 4) |
| Public GitHub repo with an open-source license | Phase 1 (LICENSE) and Phase 9 (make public, verify) |
| Be ready to demo a working project | Phase 7 (replay mode, test scenarios), Phase 8 (DEMO.md) |
| Clearly explain what was built and how the AI contributes | README sections "How the AI contributes" and "Architecture" (Phase 8) |
| Team of 2 to 4, each member registers individually | Section 11 (workstreams) |
| Event 9:00 AM to 3:30 PM, laptop charged, student ID, check-in, WhatsApp community | Section 12 (human checklist) |

---

## 3. Product spec

**One-liner:** A camera-watching tool that stays silent until something changes, then uses Gemma 4 to say *what* changed, logs it on a timeline, and fires alerts for user-written rules.

**Why it is not a chat wrapper:**
- It is a **continuous loop**, not a one-shot prompt.
- A **cheap pixel check** (OpenCV) decides *when* to call the model, so most frames cost nothing.
- A **settle step** waits until motion stops, so the model sees the final state, not a hand mid-air.
- A **budget guard** caps model calls per minute.
- **Rules** (for example "notify me if the door is opened") are checked against every change.
- It runs **fully offline** with an open-weight model.

**Core user flow:**
1. Pick a source (webcam, phone IP camera, video file, or image folder) and a backend (local Ollama or Gemini API).
2. Type alert rules, one per line.
3. Press Start. The first frame becomes the reference.
4. Every N seconds: grab frame → cheap diff → if large and settled → ask Gemma 4 → log event → check rules → alert.
5. Timeline shows each event with before/after images, latency and which backend answered.

**Out of scope (do NOT build):** user accounts, cloud storage, video recording, object tracking, face recognition, mobile app.

---

## 4. Tech stack

| Layer | Choice | Notes |
|---|---|---|
| Language | Python 3.10+ | |
| Camera and diff | `opencv-python`, `numpy` | |
| Images | `pillow` | resize and encode for the model |
| UI | `streamlit` (use `st.fragment(run_every=...)`) | |
| Model A (local, default) | **Gemma 4 via Ollama**, `ollama` Python package | tag `gemma4:e4b` (default variant); `gemma4:e2b` if the laptop is slow |
| Model B (hosted) | **Gemma 4 via Gemini API**, `google-genai` package | IDs seen in docs: `gemma-4-31b-it`, `gemma-4-26b-a4b-it`; confirm with `client.models.list()` |
| Config | `python-dotenv` | |
| Tests | `pytest` | |
| License (code) | MIT or Apache-2.0 | Gemma model weights have their own terms; link them in the README after checking the current Gemma 4 license page |

---

## 5. Agent skills and docs to install first (optional but recommended)

These come from the skills.sh ecosystem. Skills are community-driven, so skim each `SKILL.md` before trusting it.

```bash
# Official Gemini API skill: keeps SDK usage and model IDs current
npx skills add google-gemini/gemini-skills --skill gemini-api-dev --global

# Official Streamlit skill: session state, fragments, layouts
npx skills add streamlit/agent-skills --skill developing-with-streamlit

# Meta-skill: lets the agent search skills.sh on demand (e.g. "opencv", "pytest", "readme")
npx skills add vercel-labs/skills@find-skills -g -y

# Optional: live Gemini API docs over MCP
npx add-mcp "https://gemini-api-docs-mcp.dev"
```

If `npx` is unavailable or a skill fails to install, continue without it and read the official docs directly.

---

## 6. Architecture and repo layout

```
whatchanged/
├── plan.md
├── README.md
├── DEMO.md
├── NOTES.md                  # agent decisions and open questions
├── LICENSE
├── .gitignore                # .env, venv/, events/, __pycache__/, *.jpg except samples/
├── .env.example
├── requirements.txt          # pinned after install
├── app.py                    # Streamlit UI (thin, no business logic)
├── whatchanged/
│   ├── __init__.py
│   ├── config.py             # Settings dataclass + env loading
│   ├── sources.py            # frame sources: webcam, URL, video file, image folder
│   ├── detect.py             # cheap change detector (lighting-robust)
│   ├── imaging.py            # resize, JPEG encode, side-by-side stitch
│   ├── prompts.py            # prompt templates
│   ├── report.py             # ChangeReport dataclass + robust JSON parsing
│   ├── backends/
│   │   ├── __init__.py       # get_backend(name, settings)
│   │   ├── base.py           # Backend protocol
│   │   ├── ollama_backend.py
│   │   └── gemini_backend.py
│   ├── engine.py             # Watcher: loop logic, settle, budget guard, async inference
│   ├── store.py              # JSONL event log + image files
│   └── cli.py                # headless runner for testing and replay
├── samples/                  # people-free demo frames
└── tests/
    ├── test_detect.py
    ├── test_report.py
    ├── test_engine.py        # uses a fake backend, no network
    └── test_sources.py
```

**Data flow:**

```
FrameSource ─► Watcher.step() ─► detect.change_score ─(below threshold)─► skipped++
                    │
                    └─(above, then settled)─► BackendJob (background thread)
                                                  │
                                       ChangeReport (changes, triggered_rule_ids)
                                                  │
                                      store.append_event ─► UI timeline + alert banner
```

---

## 7. Phases

Time labels are relative to when coding starts (T+). Map them to the real clock once organizers confirm when hacking begins. **Set a code freeze 45 minutes before the submission deadline.**

### Phase 1 — Repo bootstrap (T+0:00 to 0:10)

**Tasks**
1. `git init`, create the folder structure from section 6 (empty modules with docstrings are fine).
2. Add `LICENSE` (MIT or Apache-2.0, with the team's names and 2026).
3. Add `.gitignore` (must include `.env`, `venv/`, `events/`, `__pycache__/`, `.pytest_cache/`).
4. Add `.env.example`:
   ```
   WC_BACKEND=ollama            # ollama | gemini
   OLLAMA_MODEL=gemma4:e4b
   OLLAMA_HOST=http://localhost:11434
   GEMINI_API_KEY=
   GEMINI_MODEL=gemma-4-31b-it
   ```
5. Create venv, install: `streamlit opencv-python numpy pillow google-genai ollama python-dotenv pytest`. Then `pip freeze` the direct dependencies into `requirements.txt`.
6. Write a 10-line placeholder `README.md` (title and one-liner).
7. Create the GitHub repo (public) and push. Set repo topics: `gemma`, `open-source-ai`, `computer-vision`, `ollama`, `streamlit`.

**Acceptance**
- `git log` shows at least 2 commits; `git status` is clean.
- `git check-ignore .env` prints `.env`.
- `pip install -r requirements.txt` works in a fresh venv.

**Commit:** `chore: bootstrap repo, license, gitignore, env template`

---

### Phase 2 — Frame sources (T+0:10 to 0:20)

**Goal:** one interface for all inputs so the demo can never be blocked by a bad camera.

**Tasks** (`whatchanged/sources.py`)
1. Define `class FrameSource` with `read() -> np.ndarray | None` (BGR frame) and `close()`.
2. Implement:
   - `WebcamSource(index: int)`: discard 2 to 3 buffered frames before each real read.
   - `UrlSource(url: str)`: for phone apps like IP Webcam (`http://IP:8080/video`).
   - `VideoFileSource(path, step_seconds)`: advances through a recorded video, looping.
   - `ImageFolderSource(path)`: steps through sorted images, looping. Used for tests and the offline demo.
3. `open_source(spec: str)`: digits → webcam, `http(s)://` → URL, directory → image folder, file → video.
4. Handle failures by returning `None`, never by crashing.

**Acceptance** (`tests/test_sources.py`)
- Image-folder source returns frames in order and loops.
- `open_source("nonexistent")` raises a clear `ValueError`.

**Commit:** `feat(sources): webcam, url, video and image-folder frame sources`

---

### Phase 3 — Cheap change detector (T+0:20 to 0:35)

**Goal:** decide "did the scene meaningfully change?" with zero model calls.

**Tasks** (`whatchanged/detect.py`)
1. `change_score(prev, curr, *, size=(320, 240), blur=21, pixel_threshold=25) -> float`, returning the percentage of pixels that changed:
   - resize both, convert to grayscale, Gaussian blur;
   - **normalize brightness**: shift `curr` so its mean equals `prev`'s mean (ignores lights turning on/off);
   - `absdiff`, count pixels above `pixel_threshold`, return percent.
2. Optional region of interest `roi=(x, y, w, h)` as fractions 0 to 1. If given, only that region is compared.
3. Keep it pure (no I/O), so it is easy to test.

**Acceptance** (`tests/test_detect.py`, synthetic numpy images, no camera)
- identical frames → score under 0.1
- uniform brightness shift of +40 → score under 1.0
- small Gaussian noise → score under 1.0
- a 20% area white rectangle added → score above 5.0
- ROI that excludes the rectangle → score under 1.0

**Commit:** `feat(detect): lighting-robust pixel change score with ROI + tests`

---

### Phase 4 — Model backends and the integration spike (T+0:35 to 1:05)

**Goal:** Gemma 4 answers "what changed?" through either backend, returning structured data.

**Tasks**
1. **`imaging.py`**: `to_jpeg_bytes(frame, max_side=768, quality=85)` and `side_by_side(before, after)` (labels "BEFORE" and "AFTER" drawn on the image).
2. **`report.py`**:
   ```python
   @dataclass
   class ChangeReport:
       changes: list[str]            # short human sentences
       triggered_rule_ids: list[int] # indexes into the rules list
       raw: str = ""
       parse_error: bool = False
   def parse_report(text: str, n_rules: int) -> ChangeReport: ...
   ```
   - Strip markdown fences, find the first `{...}` block, `json.loads`.
   - Drop rule IDs outside `0..n_rules-1`.
   - On failure return an empty report with `parse_error=True`. Never raise.
3. **`prompts.py`**: build one prompt that:
   - says image 1 is BEFORE and image 2 is AFTER from a fixed camera;
   - asks only for real changes (objects added, removed, moved; doors/drawers opened or closed; people entering or leaving);
   - tells the model to ignore lighting, shadows, reflections, compression noise;
   - lists rules **numbered from 0** and asks for the numbers of rules that were triggered;
   - demands raw JSON only: `{"changes": ["..."], "triggered_rule_ids": [0]}`; empty lists if nothing changed.
4. **`backends/base.py`**: `Backend` protocol with `describe_change(before, after, rules: list[str]) -> ChangeReport` and a `name` string.
5. **`backends/ollama_backend.py`**: call `ollama.chat` with the model from settings, `images=[...]` (JPEG bytes), `format="json"` if supported, `temperature=0`.
6. **`backends/gemini_backend.py`**: `google-genai` client, `generate_content` with prompt plus images. Do **not** assume JSON mode is supported for Gemma models; rely on `parse_report`.
7. **Retry:** one retry with 1s backoff on transient errors or parse errors. After that, return an error report (do not crash the loop).
8. **Integration spike (do this before polishing):** write `scripts/spike.py` that sends two sample images through each backend and prints the raw text and latency.
   - Test **two separate images** first. If the model rejects them or ignores the second, switch that backend to `side_by_side` mode (one stitched image, prompt says "left is BEFORE, right is AFTER"). Make this a setting: `image_mode = "two_images" | "side_by_side"`.
   - Record the working configuration and measured latency in `NOTES.md`.
9. `backends/__init__.py`: `get_backend(name, settings)`.

**Acceptance**
- `tests/test_report.py` covers: clean JSON, JSON in code fences, JSON with extra prose, garbage text, out-of-range rule IDs.
- With Ollama running (`ollama pull gemma4:e4b` already done), the spike returns a parsed `ChangeReport` for a pair where an object was added.
- Same with a Gemini API key, if available. If not, the local path alone is sufficient.

**Fallbacks**
- Ollama too slow (more than 30s per call): use `gemma4:e2b`, lower `max_side` to 512.
- Gemini rejects the model ID: list models with the SDK and pick the available Gemma 4 ID.

**Commit:** `feat(backends): Gemma 4 via Ollama and Gemini API with robust JSON parsing`

---

### Phase 5 — The engine: loop logic, settle step, budget guard (T+1:05 to 1:25)

**Goal:** all behavior lives in a testable `Watcher`, with no Streamlit code.

**Tasks** (`whatchanged/engine.py`)
1. `Watcher(source, backend, settings, rules)` with a non-blocking `step()` that returns a list of new `Event`s (usually empty). Called once per tick by the UI or CLI.
2. State: `reference`, `candidate`, `pending_future`, and counters `frames_seen`, `skipped`, `model_calls`, `errors`, `last_latency_ms`.
3. Logic per tick:
   1. Read a frame. If `None`, count an error and return.
   2. If no reference yet: set it and return.
   3. If a model job is pending: collect its result if finished, otherwise return (keep showing "analyzing").
   4. `score = change_score(reference, frame)`.
   5. If `score < threshold`: `skipped += 1`, clear any candidate, return.
   6. **Settle:** if there is no candidate, store this frame as `candidate` and return. If there is a candidate and `change_score(candidate, frame) < threshold`, the scene is stable, so go on. Otherwise replace the candidate and return.
   7. **Budget guard:** if calls in the last 60s ≥ `max_calls_per_min`, keep the candidate and return.
   8. Submit `backend.describe_change(reference, candidate, rules)` to a single-worker `ThreadPoolExecutor`. Worker code must never touch `st.*`.
   9. When the result arrives: if `changes` is non-empty, create an `Event` (id, timestamp, changes, triggered rule texts, before/after JPEG bytes, diff percent, latency, backend name). Either way set `reference = candidate`.
4. `reset_reference()`, `update_rules(rules)`, `stats()` (including `calls_saved_percent = skipped / frames_seen`).
5. **`store.py`:** `append_event(event)` writes a line to `events/events.jsonl` and images to `events/img/`. `load_events()` for restart. Add `export_markdown(events)` for a shareable timeline.
6. **`cli.py`:** `python -m whatchanged.cli --source samples/ --backend ollama --interval 1` runs the watcher headless and prints events. Used for replay and smoke tests.

**Acceptance** (`tests/test_engine.py`, with a `FakeBackend` and an `ImageFolderSource`; no network, no camera)
- Static frames → `model_calls == 0`, `skipped` increases.
- One real change → exactly one model call, one event.
- A change that keeps moving for 2 ticks, then settles → one call, made on the settled frame.
- With `max_calls_per_min=1` and two changes in a row → second call is deferred.
- Backend raising an exception → `errors` increases, loop continues.
- Rules: `triggered_rule_ids=[0]` maps to the right rule text in the event.

**Commit:** `feat(engine): watcher loop with settle step, budget guard, async inference`

---

### Phase 6 — Streamlit UI (T+1:25 to 1:50)

**Goal:** a clean demo UI. `app.py` stays thin. All logic is imported from the package.

**Tasks**
1. Use the Streamlit skill (if installed) for session state and fragment patterns.
2. **Sidebar**
   - Source text input (default `0`) with a hint listing webcam index, phone URL, video path, folder path.
   - Backend radio: "Local (Ollama)" or "Gemini API", plus model name input.
   - Rules text area (one per line), prefilled with `notify me if the door is opened`.
   - Interval slider 3 to 30s (default 5), sensitivity slider 0.5 to 10% (default 2.0), max calls per minute (default 6).
   - Start/Stop toggle, "Reset reference" button, "Save snapshot to samples/" button.
3. **Main area**
   - Live frame with a status chip: Watching, Settling, Analyzing, Stopped, Error.
   - Metric row: frames checked, skipped, model calls, **% of frames that needed no AI** (the headline number), last latency, active backend.
   - Red alert banner for the most recent triggered rule (with a ten-second fade or dismiss button).
   - Timeline of events, newest first: time, bullets of changes, before/after images, triggered rules highlighted.
   - "Download timeline (.md)" button using `export_markdown`.
4. Keep the `Watcher` and camera in `st.session_state` (or `st.cache_resource`) so reruns do not reopen the camera. Release the camera on Stop.
5. Show friendly errors for: camera not available, Ollama not running (with the command to fix it), missing API key.
6. **Stretch (only if ahead of schedule):** audible beep on alert; Telegram bot alert via `requests`; "Summarize this session" button that sends the event log to Gemma 4 for a 3-line recap; ROI picker.

**Acceptance**
- `streamlit run app.py` loads with no exceptions on a machine with no camera (shows the friendly error).
- With the sample-folder source and the local backend: start → timeline fills → metrics update without freezing the live view while the model is thinking.
- Switching backend and restarting works without restarting Streamlit.

**Commit:** `feat(ui): Streamlit dashboard with live view, metrics, timeline and alerts`

---

### Phase 7 — Hardening and demo scenarios (T+1:50 to 2:05)

**Tasks**
1. Capture 4 to 6 **people-free** sample frames with the snapshot button and commit them in `samples/` (empty desk, object added, object moved, object removed, door/drawer open). Name them in order: `01_empty.jpg`, `02_bottle_added.jpg`, and so on.
2. Run these scenarios, once on the live webcam and once on the `samples/` replay:

   | # | Scenario | Expected |
   |---|---|---|
   | 1 | Nothing changes for 60s | 0 model calls, skipped counter rises |
   | 2 | Add a bottle | 1 event: bottle added |
   | 3 | Move the bottle | 1 event: bottle moved |
   | 4 | Toggle room light | no event (or an empty change list) |
   | 5 | Open the door/drawer with the rule set | alert banner fires |
   | 6 | Wave a hand continuously for 10s | settle step prevents a flood of calls |
   | 7 | Unplug Wi-Fi with the local backend | still works |

3. Tune defaults (threshold, interval, `max_side`) from what you observed. Write the final values into `.env.example` and the README.
4. Run `pytest -q`. Fix failures.
5. **Secret scan before the repo goes public:** `git log -p | grep -i -E "api[_-]?key|AIza"` must show nothing real, and `git ls-files | grep -E "\.env$"` must be empty.

**Acceptance:** scenarios 1, 2, 5 and 7 pass on the real webcam; all tests pass; no secrets in history.

**Commit:** `test: demo scenarios, sample frames, tuned defaults`

---

### Phase 8 — Documentation and demo script (T+2:05 to 2:30)

**README.md must contain, in this order:**
1. Title, one-line pitch, and a screenshot or short GIF of the timeline plus alert banner.
2. **Problem:** cameras record everything; asking an AI about every frame is slow and expensive.
3. **How it works:** the data-flow diagram (Mermaid block) from section 6, in plain words.
4. **How the AI contributes:** Gemma 4 does the part pixels cannot (understanding which changes are meaningful, naming objects, judging rules in natural language). The code decides when to ask and what to do with the answer. State that Gemma 4 runs locally through Ollama, so no frame leaves the machine.
5. **Why open-weight matters here:** privacy, offline operation, no per-call cost, and the user can swap the model.
6. **Quickstart (local):** install Ollama, `ollama pull gemma4:e4b`, create venv, `pip install -r requirements.txt`, `streamlit run app.py`.
7. **Quickstart (Gemini API):** copy `.env.example` to `.env`, set the key and model.
8. **Using a phone as the camera:** IP Webcam URL.
9. **Configuration table** (every env var and slider).
10. **Tests:** `pytest -q`.
11. **Limitations:** honest list (fixed camera only, lighting extremes, small objects, model latency on CPU).
12. **Roadmap:** ROI, Telegram alerts, session summaries, multi-camera.
13. **Built with AI assistance** note, **model license** note and link, **License** (code), **Acknowledgments** (Gemma / Google DeepMind, C³ × Hacktoberfest Hack Day).

**DEMO.md** (the 90-second script, one line per beat):
1. "Normal cameras record everything. This one only thinks when something changes." Show the % of frames needing no AI.
2. Remove or add an object. Timeline logs it with before/after.
3. Type a new rule live ("alert me if a bag is left here"), then trigger it. Alert fires.
4. Disconnect Wi-Fi, trigger another change. Still works, because Gemma 4 runs locally.
5. Close: "The cheap check decides *when*. Gemma 4 explains *what*. Open-weight, so it is private by design."

Also include a fallback line: "If the camera fails, switch the source to `samples/` and run the same demo."

**Acceptance:** a stranger can clone the repo and run the local quickstart from the README alone. Verify by following the README in a fresh folder.

**Commit:** `docs: README, DEMO script, screenshots`

---

### Phase 9 — Submission and freeze (finish at least 30 min before the deadline)

1. Make sure the repo is **public**, has a LICENSE, and the README renders correctly on GitHub.
2. Tag the final commit: `git tag v1.0-hackday && git push --tags`.
3. Re-run the secret scan from Phase 7 on the final history.
4. Fill in the official submission form with: repo link, one-paragraph description, the "How the AI contributes" paragraph, and the demo notes. Confirm the exact form and deadline with the organizers (I could not verify them from the guidelines document).
5. Rehearse the demo twice with the real laptop, charger plugged in, on the venue Wi-Fi and on the local backend.
6. Freeze: no feature work after this point, only fixes.

---

## 8. Cut list (drop in this order if behind schedule)

1. Telegram and beep alerts
2. Session summary and ROI picker
3. Markdown export
4. Gemini API backend (keep Ollama only; it satisfies the open-weight requirement on its own)
5. Settle step (keep only if the engine tests already pass)

**Never cut:** frame sources replay mode, change detector tests, README, LICENSE, secret scan.

## 9. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Local model too slow on a CPU laptop | Use `gemma4:e2b`, smaller `max_side`, longer interval; non-blocking inference keeps the UI live |
| Model rejects two images | `side_by_side` image mode (Phase 4 spike) |
| Model returns invalid JSON | `parse_report` never raises; one retry; error report shown in UI |
| Free-tier API rate limits | `max_calls_per_min` guard; local backend as default |
| Webcam blocked or busy (Zoom/Meet open) | Replay mode from `samples/`; try camera index 1; phone IP camera |
| Venue Wi-Fi is bad | Local backend works offline |
| Secret leaked in a public repo | `.gitignore`, `.env.example`, scan in Phases 7 and 9 |
| Too many false alerts from lighting | Brightness normalization plus the prompt's "ignore lighting" rule; tune threshold |

## 10. Definition of done

- [ ] Public repo with LICENSE, README, DEMO.md, tests passing
- [ ] Runs fully locally with Gemma 4 through Ollama; Gemini API backend works if a key is provided
- [ ] Headline metric visible in the UI: % of frames that needed no AI call
- [ ] At least one rule alert demonstrated live
- [ ] Settle step demonstrated (continuous motion does not spam the model)
- [ ] No secrets or personal images in git history
- [ ] README explains what was built and how the AI contributes
- [ ] Demo rehearsed with fallback to `samples/`

## 11. Team workstreams (teams are 2 to 4 people)

| Person | Owns | Phases |
|---|---|---|
| A | Detector and engine | 2, 3, 5 |
| B | Backends and prompts | 4 |
| C | Streamlit UI | 6 |
| D (or shared) | Tests, README, demo, submission | 7, 8, 9 |

With 2 people: A+D and B+C. Agree on the interfaces in section 6 first (`FrameSource`, `Backend`, `ChangeReport`, `Watcher.step()`) so work can proceed in parallel, then merge with small PRs.

## 12. Human checklist (not for the agent)

**Before the event**
- [ ] Every team member registered individually for the event
- [ ] Everyone joined the C³ Hackstorm WhatsApp Community
- [ ] Install Ollama and run `ollama pull gemma4:e4b` (and `gemma4:e2b` as a backup) on the demo laptop; tools and models are fine to prepare in advance, but do **not** write project code before the event
- [ ] Get a Gemini API key from Google AI Studio (optional, for the hosted backend)
- [ ] Install Node.js if you want the `npx skills` commands
- [ ] Test the webcam, and install a phone IP-camera app as a backup

**What to carry**
- [ ] College/student ID
- [ ] Laptop, fully charged, with charger
- [ ] Extension cable or power strip
- [ ] Water bottle

**At the venue**
- [ ] Complete the event check-in on arrival
- [ ] Stay for the whole event (9:00 AM to 3:30 PM)
- [ ] Confirm the hacking start time and submission deadline with the organizers
- [ ] Keep your workspace clean

**Do last:** make the repo public, submit, and rehearse the demo twice.
