# 🏟️ StadiumOps AI

**A GenAI-powered real-time decision support assistant for FIFA World Cup 2026 stadium control rooms.**

Built for Main Challenge 4 — *Smart Stadiums & Tournament Operations*.

---

## 1. Chosen Vertical

**Real-Time Decision Support**, for stadium control-room staff (organizers, volunteers, on-ground operations teams).

This vertical was chosen because it naturally connects to the other tracks mentioned in the problem statement instead of treating them as separate silos:

- **Dynamic crowd management** feeds the decision engine (gate/zone density, queue times).
- **Smart indoor navigation** is expressed as an output of the decisions (which gate/route to redirect fans toward).
- **Multi-language assistance** is used as the communication layer for both staff and fans.

So the system is a single coherent assistant, not four disconnected demos.

## 2. Approach and Logic

The system is split into two deliberately separate layers:

### Layer 1 — Deterministic rule-based triage (`decision_engine.py`)
Safety- and operations-critical decisions (which gate is overcrowded, which incident needs attention) are made with **plain, auditable Python logic**, not an LLM. This is a conscious design choice: a stadium control room cannot depend on an LLM being available, fast enough, or non-hallucinating to know that Gate 3 is at 92% capacity. Rules are simple thresholds:

- Gate density ≥ 85% → **critical**
- Gate queue ≥ 15 minutes → **warning**
- The least-congested gate is automatically suggested as a redirection target.

### Layer 2 — GenAI explanation & communication (`decision_engine.py`, powered by Google Gemini)
Once the facts are known, GenAI is used for what it's actually good at:
- Turning structured data into a clear, human-readable recommendation for staff.
- Answering free-text staff questions ("What's happening at Gate 3?") grounded only in the current live data (so it can't invent facts not present in the snapshot).
- Translating public alerts into the fan's language on demand (multi-language assistance).

**Fallback by design:** if `GEMINI_API_KEY` is not set, or the API call fails for any reason, the app automatically falls back to the deterministic summary instead of crashing or blocking the control room dashboard. This was a deliberate reliability decision, not an afterthought.

### Live data (`mock_data.py`)
Since real stadium IoT sensors aren't available for this hackathon, live venue signals (gate crowd density, queue times, concourse zone density/temperature, weather, and randomly-arriving incident reports) are simulated with realistic ranges. In a production deployment, `mock_data.py` would be replaced by real feeds from turnstile counters, CCTV-based crowd density models, and a staff incident-reporting API — the rest of the system (`decision_engine.py`, `app.py`) would not need to change, since they only depend on the snapshot's data shape.

## 3. How the Solution Works

1. `mock_data.get_full_snapshot()` generates a live snapshot of all gates, zones, weather, and any new incident.
2. `decision_engine.build_context_summary()` runs the rule-based triage and reduces the raw snapshot into the facts that matter (flagged gates, best relief gate, active incident).
3. `decision_engine.generate_recommendation()` sends that structured context to Gemini (or falls back to a deterministic sentence) to produce a plain-English recommendation for staff.
4. The Streamlit dashboard (`app.py`) displays gate/zone status, weather, incidents, the GenAI recommendation, an auto-translated public announcement, and a free-text Q&A box for staff.
5. Staff can ask natural-language questions; answers are grounded strictly in the current snapshot, and the system is explicit when GenAI isn't configured, rather than silently guessing.

### Run it locally
```bash
git clone <your-repo-url>
cd stadiumops-ai
pip install -r requirements.txt
cp .env.example .env        # then add your free Gemini API key
streamlit run app.py
```
The app works even without a `GEMINI_API_KEY` set — it will just use the rule-based fallback text instead of live GenAI output.

### Run tests
```bash
pytest tests/ -v
```

## 4. Assumptions Made

- Real-time sensor data (crowd density, turnstile counts) is not available in this environment, so it is simulated with realistic random ranges rather than sourced from live hardware.
- A single Gemini API key is sufficient to demonstrate the GenAI layer; no fine-tuning or custom model hosting was required for this scope.
- "Multi-language assistance" is scoped to translating staff recommendations and public alerts on demand, rather than building a full multilingual voice interface, to keep the solution focused and within the repository size constraints.
- The rule thresholds (85% density, 15-minute queue) are illustrative defaults for a hackathon demo; a real deployment would tune these per-venue with operations staff.

## 5. Project Structure
```
stadiumops-ai/
├── app.py                    # Streamlit control-room dashboard (UI)
├── decision_engine.py         # Rule-based triage + GenAI recommendation/translation layer
├── mock_data.py                # Simulated live venue telemetry
├── requirements.txt
├── .env.example
├── .gitignore
├── tests/
│   └── test_decision_engine.py   # Unit tests for the deterministic rule engine
└── README.md
```

## 6. Security Notes
- No API keys are hardcoded or committed; `.env` is git-ignored and `.env.example` is provided as a template.
- All GenAI calls are wrapped in try/except so a third-party API failure cannot crash or block the control room dashboard.
- Staff Q&A answers are explicitly grounded in the current live snapshot to reduce the risk of the assistant inventing information during an operational incident.

## 7. Accessibility
- Clear color-coded status icons (🔴🟠🟢) alongside text labels, not color alone.
- Multi-language output for both staff and public-facing announcements.
- Simple, linear dashboard layout suitable for fast scanning under control-room time pressure.
