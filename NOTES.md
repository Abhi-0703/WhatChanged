# Engineering Notes & Log — What Changed?

## 1. Environment Check Results
- **Python Version**: Python 3.12.15 (installed via Homebrew for clean NumPy/OpenCV prebuilt wheel support; default system environment was Python 3.14.7 / macOS 3.9.6)
- **Pip Version**: 26.2.1
- **Git Version**: 2.54.0 (Apple Git-157)
- **Ollama**: Installation initiated via Homebrew (`brew install ollama`). Local Ollama service is not running yet; `gemma4:e4b` is not pulled yet. Local fallback / fake backend & clear user-facing guidance are enabled.
- **Camera**: OpenCV test reported `OpenCV: not authorized to capture video` (macOS TCC permissions require GUI user authorization for camera access). Replay mode and synthetic testing work out-of-the-box.
- **GEMINI_API_KEY**: Not set in environment. Gemini backend handles missing key gracefully with clear UI instructions; local Ollama is the primary default backend.
- **Node/npx**: Installed (`v22.x` / `/usr/local/bin/npx`). Streamlit agent skill installed (`developing-with-streamlit`).

## 2. Event Rules vs. Plan Alignment
- **Event Rules**: C³ × Hacktoberfest Hack Day rules require:
  1. Team of 2–4 members, each individually registered.
  2. Original project built during the Hack Day with meaningful technical contributions.
  3. Open-source / open-weight AI as a core component (satisfied via open-weight Gemma 4).
  4. Public GitHub repository with open-source license (MIT License added).
  5. Working demo with clear explanation of what was built and how AI contributes.
  6. Code of Conduct & venue cleanliness.
- **Alignment**: Plan.md strictly satisfies all event rules. No conflicts found.

## 3. Architecture Decisions & Spikes
- **Default Backend Selection**: Switched default backend to **Gemini API** using open-weight Gemma 4 (`gemma-4-26b-a4b-it` verified in official Google Gemini API April 2026 changelog and docs). This provides immediate, zero-download hosted inference.
- **On-Device Local Option**: Maintained full `OllamaBackend` support defaulting to lightweight `gemma4:e2b` for privacy and offline usage without 17 GB storage overhead.
- **HTTP 429 Rate-Limit Interception**: Automatically catches HTTP 429 and `RESOURCE_EXHAUSTED` responses, applies exponential backoff with retry, and displays a friendly `"RATE LIMITED (SLOWING DOWN)"` badge while pausing new calls for 15s. Default `WC_MAX_CALLS_PER_MIN` reduced to 4.
- **Offline Response Cache (`ResponseCache`)**: Built image-hash cache seeded with sample frame transitions (`01_empty_desk.jpg` through `05_bottle_removed.jpg`). Guarantees that replay mode runs with **zero network dependencies**, 0ms latency, and no API keys required.
- **Phase 4 Integration Spike Results (`scripts/spike.py`)**:
  - Evaluated `two_images` vs `side_by_side` image input modes.
  - Decision: Set `side_by_side` as the default `WC_IMAGE_MODE`. Stitching into a single canvas with clear "BEFORE" and "AFTER" headers is universally supported across local Ollama vision backends and remote endpoints without requiring multi-part image array support.
  - Verified `FakeBackend`: Latency 0 ms, parsed `ChangeReport` with canned changes and rules.
  - Verified `OllamaBackend`: Safely captures offline connection errors, retries with 1s backoff (1034 ms total elapsed), and produces a clean non-crashing error report.
  - Verified `GeminiBackend`: Detects missing `GEMINI_API_KEY` instantly and yields informative configuration guidance.
- **Decision (Robust JSON Parsing)**: Models frequently enclose JSON responses in markdown fences (````json ... ````) or include explanatory text. Implemented regex-based JSON extraction in `report.py` that safely extracts the JSON payload and falls back gracefully without crashing.
- **Decision (Pure Watcher Loop)**: `Watcher` class in `engine.py` is pure Python and isolated from any Streamlit dependencies, allowing headless execution, CLI replay, and robust unit testing.

## 4. Needs Human Verification List
1. **Camera Permissions on macOS**: Run `python -c "import cv2; cap=cv2.VideoCapture(0); print(cap.read()[0])"` in a standard Terminal window to trigger the macOS Camera Permission modal and click "Allow".
2. **Live Gemini API Key & Gemma 4 Call**: Provide a live `GEMINI_API_KEY` from Google AI Studio in `.env` or the UI sidebar to verify live cloud inference against `gemma-4-26b-a4b-it`. (Not tested live by agent to avoid assuming external key validity).
3. **Local Ollama & Gemma 4 (Optional)**: If testing on-device privacy mode, run `brew services start ollama` and `ollama pull gemma4:e2b`.
4. **Live Room Snapshots**: Use the in-app "Save snapshot" button to capture people-free sample frames of an empty desk and added objects.
5. **Offline Wi-Fi Verification**: Run `streamlit run app.py` with Frame Source set to `samples/` (or Ollama backend), disconnect Wi-Fi, and verify continuous detection and timeline events work with zero network connection.
6. **Publish Repo & Submit**: Push to GitHub public repository and submit the project link before the hackathon deadline.
