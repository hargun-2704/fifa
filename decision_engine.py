"""
decision_engine.py
Core "brain" of StadiumOps AI.

Two layers, deliberately kept separate so they can be unit-tested independently:

1. Rule-based triage (deterministic, fast, no API calls, no cost) --
   decides WHAT needs attention right now from a live data snapshot.

2. GenAI explanation/recommendation layer (calls Google Gemini) --
   turns the deterministic findings into a clear, human-readable,
   and optionally multilingual recommendation for control-room staff.

Keeping rules and GenAI separate matters for a stadium-scale system:
safety-critical triage should never depend on an LLM being available,
network latency, or hallucination risk. GenAI is used to *explain and
communicate* decisions, not to make the underlying safety judgement.
"""

import os
from functools import lru_cache
from typing import Dict, List

try:
    from dotenv import load_dotenv
    load_dotenv()  # reads .env in the project root into os.environ, if present
except ImportError:
    pass  # dotenv not installed -- fall back to real environment variables only

try:
    from google import genai
    _GEMINI_AVAILABLE = True
except ImportError:
    _GEMINI_AVAILABLE = False

GEMINI_MODEL = "gemini-2.5-flash"

DENSITY_CRITICAL = 85
DENSITY_BUSY = 60
QUEUE_ALERT_MINUTES = 15


# ---------------------------------------------------------------------------
# Layer 1: Deterministic rule-based triage
# ---------------------------------------------------------------------------

def triage_gates(gates: List[Dict]) -> List[Dict]:
    """Flag gates that need operational attention, ranked by severity."""
    flagged = []
    for g in gates:
        if g["density_pct"] >= DENSITY_CRITICAL or g["queue_minutes"] >= QUEUE_ALERT_MINUTES:
            severity = "critical" if g["density_pct"] >= DENSITY_CRITICAL else "warning"
            flagged.append({**g, "severity": severity})
    flagged.sort(key=lambda x: x["density_pct"], reverse=True)
    return flagged


def find_relief_gate(gates: List[Dict]) -> Dict | None:
    """Find the least congested gate, used as a redirection target."""
    if not gates:
        return None
    return min(gates, key=lambda g: g["density_pct"])


def build_context_summary(snapshot: Dict) -> Dict:
    """Reduce a raw snapshot into the structured facts staff actually need."""
    flagged_gates = triage_gates(snapshot["gates"])
    relief_gate = find_relief_gate(snapshot["gates"])
    return {
        "flagged_gates": flagged_gates,
        "relief_gate": relief_gate,
        "incident": snapshot.get("incident"),
        "weather": snapshot.get("weather"),
    }


# ---------------------------------------------------------------------------
# Layer 2: GenAI explanation / recommendation / multilingual communication
# ---------------------------------------------------------------------------

_client = None


def _configure_gemini() -> bool:
    """Lazily create a Gemini client if an API key is available."""
    global _client
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not (_GEMINI_AVAILABLE and api_key):
        return False
    if _client is None:
        _client = genai.Client(api_key=api_key)
    return True


def _fallback_recommendation(context: Dict) -> str:
    """Deterministic, no-API-needed fallback so the app always demos correctly."""
    lines = []
    if context["flagged_gates"]:
        worst = context["flagged_gates"][0]
        relief = context["relief_gate"]
        lines.append(
            f"ALERT: {worst['gate']} is at {worst['density_pct']}% capacity "
            f"with a {worst['queue_minutes']}-minute queue."
        )
        if relief and relief["gate"] != worst["gate"]:
            lines.append(
                f"Recommended action: redirect incoming fans toward {relief['gate']} "
                f"(currently only {relief['density_pct']}% capacity)."
            )
    if context["incident"]:
        inc = context["incident"]
        lines.append(
            f"Incident reported at {inc['location']}: {inc['type']} "
            f"(severity: {inc['severity']}). Dispatch nearest available staff."
        )
    if not lines:
        lines.append("All gates and zones nominal. No action required.")
    return "\n".join(lines)


@lru_cache(maxsize=64)
def _cached_llm_call(prompt: str) -> str:
    """Cache identical prompts within a session to save API calls/cost."""
    response = _client.models.generate_content(model=GEMINI_MODEL, contents=prompt)
    return response.text.strip()


def generate_recommendation(context: Dict, language: str = "English") -> str:
    """
    Produce a staff-facing recommendation from the triage context.
    Uses Gemini if configured; otherwise falls back to a deterministic summary
    so the system is never blocked by API availability.
    """
    fallback = _fallback_recommendation(context)

    if not _configure_gemini():
        return fallback

    prompt = (
        "You are an operations assistant inside a FIFA World Cup 2026 stadium "
        "control room. Given the structured situation data below, write a short, "
        "clear, actionable recommendation (max 4 sentences) for on-ground staff. "
        f"Respond in {language}. Be specific and calm, no extra commentary.\n\n"
        f"Situation data: {context}"
    )
    try:
        return _cached_llm_call(prompt)
    except Exception:
        # Never let an API failure take down the control room dashboard.
        return fallback


def answer_staff_query(query: str, context: Dict, language: str = "English") -> str:
    """Free-text Q&A for staff, grounded in the current live context."""
    if not query.strip():
        return ""

    if not _configure_gemini():
        return (
            "GenAI is not configured (missing GEMINI_API_KEY). "
            f"Here is the raw current context instead: {context}"
        )

    prompt = (
        "You are StadiumOps AI, an assistant for on-ground stadium staff during "
        "the FIFA World Cup 2026. Answer the staff member's question using ONLY "
        "the live situation data provided. If the data doesn't cover the question, "
        f"say so honestly. Respond in {language}, in under 4 sentences.\n\n"
        f"Live situation data: {context}\n\n"
        f"Staff question: {query}"
    )
    try:
        return _cached_llm_call(prompt)
    except Exception as e:
        return f"Could not reach GenAI service right now ({e}). Please rely on raw data panel."


def translate_alert(message: str, language: str) -> str:
    """Translate a short public alert message for multilingual fan communication."""
    if language.lower() == "english" or not message.strip():
        return message
    if not _configure_gemini():
        return message  # fallback: show original if GenAI unavailable

    prompt = (
        f"Translate the following stadium announcement into {language}. "
        "Keep it short and clear for a public announcement. "
        f"Return ONLY the translated text.\n\nMessage: {message}"
    )
    try:
        return _cached_llm_call(prompt)
    except Exception:
        return message