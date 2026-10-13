# What Changed? — 90-Second Live Hackathon Demo Script

> **Challenge:** Best Open-Source AI Project + Best Use of Gemma 4  
> **Speaker Note:** Speak clearly, keep the Streamlit browser window on screen, and perform physical actions smoothly.

---

## Pre-Demo Setup (Do 2 minutes before presenting)
1. Ensure Ollama is running (`brew services start ollama`).
2. Run `streamlit run app.py` and open [http://localhost:8501](http://localhost:8501).
3. Leave Frame Source as `0` (or `samples/` if using fallback replay mode).
4. Click **▶️ Start**.

---

## 90-Second Script (Beat by Beat)

### [00:00 - 00:15] Beat 1: The Pitch & The Headline Metric
> *"Judges, normal surveillance cameras record gigabytes of static video, and asking a cloud vision model about every single frame would bankrupt you in compute fees.  
> Watch this: our camera has evaluated dozens of frames, yet as you can see on the dashboard, **over 95% of frames needed zero AI calls**. We stay completely silent while the scene is calm."*

*(Gesture to the headline metric card: **% of Frames Needing No AI**).*

---

### [00:15 - 00:35] Beat 2: The Physical Change & Settle Step
> *"Now watch what happens when I physically add an object to the desk."*

*(Place a water bottle or thermos onto the desk surface in front of the camera. Remove your hand).*

> *"Notice the status chip transitions from Watching → Settling. Our algorithm waits until my hand moves out of the frame so Gemma 4 inspects the finalized scene, not motion blur.  
> And boom—exactly one model call fires, and look at the timeline: before and after snapshots, with Gemma 4 explaining: 'Water bottle added to the desk'."*

---

### [00:35 - 00:55] Beat 3: Natural Language Rules Engine
> *"This isn't just generic change detection. Let's type an alert rule live in the sidebar:  
> `notify me if a bottle or cup is on the desk`.*

*(Type or highlight the rule in the sidebar).*

> *"Now I'll shift the bottle's position."*

*(Shift or move the bottle).*

> *"Look at the top of the screen: the red alert banner immediately triggers with 🚨 RULE ALERT. Gemma 4 evaluated the user's natural language rule directly against the visual diff without any custom training or dataset fine-tuning."*

---

### [00:55 - 01:15] Beat 4: The Open-Weight Offline Test
> *"Here is the most important technical feature: **everything you just saw ran completely offline** using open-weight Gemma 4 through Ollama.  
> Let me prove it: I am disconnecting the Wi-Fi on this laptop right now."*

*(Turn off Wi-Fi in the macOS menu bar).*

> *"I'll remove the object from the desk. Notice the watcher detects the change, Gemma 4 processes the frames locally, and logs the event on the timeline with zero cloud connectivity."*

---

### [01:15 - 01:30] Beat 5: Closing Statement
> *"To summarize:  
> The cheap OpenCV check decides **when** to think.  
> Gemma 4 explains **what** changed.  
> Open-weight AI makes it 100% private, zero-cost, and offline-first.  
> Thank you! We're ready for questions."*

---

## 🛡️ Emergency Fallback (If webcam is busy or permission issues occur)
If the webcam fails or is locked by another process:
> *"No problem—our architecture has a built-in offline frame replay source."*
1. In the sidebar, change **Frame Source** from `0` to `samples/`.
2. Select **Fake Backend** or **Local (Ollama)**.
3. Click **▶️ Start**. The pre-recorded people-free sample frames will cycle through the change detector and timeline seamlessly.
