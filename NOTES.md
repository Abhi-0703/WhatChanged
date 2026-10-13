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
- **Decision (Image Input Mode)**: Supported both `two_images` and `side_by_side` image modes. Default to `side_by_side` with clear "BEFORE" and "AFTER" labels for universal vision model compatibility across Ollama and Gemini endpoints.
- **Decision (Robust JSON Parsing)**: Models frequently enclose JSON responses in markdown fences (````json ... ````) or include explanatory text. Implemented regex-based JSON extraction in `report.py` that safely extracts the JSON payload and falls back gracefully without crashing.
- **Decision (Pure Watcher Loop)**: `Watcher` class in `engine.py` is pure Python and isolated from any Streamlit dependencies, allowing headless execution, CLI replay, and robust unit testing.

## 4. Needs Human Verification List
1. **Camera Permissions on macOS**: Run `python -c "import cv2; cap=cv2.VideoCapture(0); print(cap.read()[0])"` in a standard Terminal window to trigger the macOS Camera Permission modal and click "Allow".
2. **Local Ollama & Gemma 4 Pull**:
   - Start Ollama: `brew services start ollama` or run `ollama serve`.
   - Pull model: `ollama pull gemma4:e4b` (or `ollama pull gemma4:e2b` on low-power hardware).
3. **Gemini API Key**: If testing the cloud fallback backend, export `GEMINI_API_KEY="your-key-here"` or add it to `.env`.
4. **Live Room Snapshots**: Use the in-app "Save snapshot" button to capture people-free sample frames of an empty desk and added objects.
5. **Offline Wi-Fi Verification**: Turn off Wi-Fi on the laptop, run `streamlit run app.py` with Ollama backend, and verify continuous detection works 100% offline.
6. **Publish Repo & Submit**: Push to GitHub public repository and submit the project link before the hackathon deadline.
