"""
app.py
StadiumOps AI -- Real-Time Decision Support Dashboard
FIFA World Cup 2026 | Smart Stadiums & Tournament Operations

Run locally:
    pip install -r requirements.txt
    streamlit run app.py
"""

import streamlit as st

from mock_data import get_full_snapshot
from decision_engine import build_context_summary, generate_recommendation, answer_staff_query, translate_alert, _configure_gemini

st.set_page_config(page_title="StadiumOps AI", page_icon="🏟️", layout="wide")

# Accessibility: skip-to-content link for keyboard/screen-reader users, and a
# focus-visible outline so keyboard navigation is always clearly indicated.
st.markdown(
    """
    <a href="#main-content" style="
        position:absolute; left:-9999px; top:0; z-index:999;
        background:#1f6feb; color:white; padding:8px 16px; border-radius:4px;
    " onfocus="this.style.left='8px'; this.style.top='8px';"
       onblur="this.style.left='-9999px';">
        Skip to main content
    </a>
    <style>
        a:focus, button:focus, input:focus, select:focus, [role="button"]:focus {
            outline: 3px solid #1f6feb !important;
            outline-offset: 2px !important;
        }
    </style>
    <div id="main-content"></div>
    """,
    unsafe_allow_html=True,
)

LANGUAGES = ["English", "Spanish", "French", "Arabic", "Portuguese", "Hindi"]

if "history" not in st.session_state:
    st.session_state.history = []

st.title("🏟️ StadiumOps AI")
st.caption("Real-time GenAI decision support for FIFA World Cup 2026 venue control rooms")

with st.sidebar:
    st.header("Settings")
    language = st.selectbox("Staff / announcement language", LANGUAGES, index=0)
    st.markdown("---")
    if _configure_gemini():
        st.success("✅ GenAI status: connected (Gemini API key detected)")
    else:
        st.warning(
            "⚠️ GenAI status: no `GEMINI_API_KEY` found. Running on the "
            "deterministic rule-based fallback so the dashboard never breaks."
        )
    refresh = st.button("🔄 Refresh live venue data", use_container_width=True)

# --- Pull a live snapshot --------------------------------------------------
snapshot = get_full_snapshot()
context = build_context_summary(snapshot)

col1, col2 = st.columns([2, 1])

STATUS_LABEL = {"critical": "Critical", "busy": "Busy", "normal": "Normal"}
STATUS_ICON = {"critical": "🔴", "busy": "🟠", "normal": "🟢"}

with col1:
    st.subheader("Gate Status")
    for g in snapshot["gates"]:
        icon = STATUS_ICON[g["status"]]
        label = STATUS_LABEL[g["status"]]
        # Status is conveyed in text ("Critical"/"Busy"/"Normal"), not by color alone,
        # so the information is accessible to screen readers and colorblind users.
        st.write(f"{icon} **{g['gate']}** — {label}, {g['density_pct']}% capacity, {g['queue_minutes']} min queue")

    st.subheader("Concourse Zones")
    for z in snapshot["zones"]:
        st.write(f"🧭 **{z['zone']}** — {z['density_pct']}% density, {z['temperature_c']}°C")

with col2:
    st.subheader("Weather")
    st.write(f"{snapshot['weather']['condition']}, {snapshot['weather']['temperature_c']}°C")

    st.subheader("Latest Incident")
    if snapshot["incident"]:
        inc = snapshot["incident"]
        st.markdown(
            f'<div role="alert" aria-live="assertive" style="'
            f'background:#3a2a10; border-left:4px solid #d97706; padding:12px 16px; '
            f'border-radius:4px; color:#f5deb3;">'
            f'[{inc["time"]}] {inc["type"]} at {inc["location"]} (severity: {inc["severity"]})</div>',
            unsafe_allow_html=True,
        )
    else:
        st.success("No new incidents reported.")

st.markdown("---")
st.subheader("🤖 GenAI Recommendation")
recommendation = generate_recommendation(context, language=language)
# aria-live="polite" ensures screen readers announce this content when it
# changes on refresh, since it updates dynamically rather than on page load.
st.markdown(
    f'<div role="status" aria-live="polite" style="'
    f'background:#1a2733; border-left:4px solid #1f6feb; padding:12px 16px; '
    f'border-radius:4px; color:#e6edf3;">{recommendation}</div>',
    unsafe_allow_html=True,
)

if context["flagged_gates"]:
    public_alert = translate_alert(
        "Please note: some gates are experiencing high congestion. "
        "Follow staff instructions for alternate entry points.",
        language,
    )
    st.markdown("**Public announcement (auto-translated):**")
    st.write(public_alert)

st.markdown("---")
st.subheader("💬 Ask StadiumOps AI")
query = st.text_input(
    "Ask a question about current venue status (e.g. 'What's happening at Gate 3?')",
    help="Answers are grounded in the live venue data shown above.",
)
if st.button("Ask StadiumOps AI") and query:
    answer = answer_staff_query(query, context, language=language)
    st.session_state.history.append((query, answer))

for q, a in reversed(st.session_state.history):
    st.markdown(f"**Staff:** {q}")
    st.markdown(f"**StadiumOps AI:** {a}")
    st.markdown("")
