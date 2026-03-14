"""QA Commander Live — Streamlit UI.

A multimodal live QA agent that:
  👁  Sees   — watches web interfaces via real-time screenshots
  👂  Hears  — listens to tester voice commands (microphone)
  🔊  Speaks — narrates findings via Gemini Live audio output
  📋  Creates — generates actionable bug reports in real time
"""

from __future__ import annotations

import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import streamlit as st

from live_agent import QARunResult, StepRecord, run_live_agent
from gemini_live import ParsedFinding

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports"
SCREENSHOTS_DIR = PROJECT_ROOT / "screenshots"

# ── Page config ────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="QA Commander Live",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Design system ──────────────────────────────────────────────────────────────

st.markdown("""
<style>
/* ── Global ── */
[data-testid="stAppViewContainer"] { background: #0d1117; }
[data-testid="stSidebar"] { background: #161b22 !important; border-right: 1px solid #30363d; }
[data-testid="stSidebar"] * { color: #c9d1d9 !important; }
h1,h2,h3,h4 { color: #e6edf3 !important; }
p, li, label { color: #8b949e !important; }
[data-testid="stMarkdownContainer"] p { color: #8b949e; }

/* ── Hero banner ── */
.hero {
    background: linear-gradient(135deg, #0d1117 0%, #161b22 50%, #0d1117 100%);
    border: 1px solid #30363d;
    border-radius: 12px;
    padding: 28px 32px;
    margin-bottom: 24px;
    position: relative;
    overflow: hidden;
}
.hero::before {
    content: '';
    position: absolute; top: 0; left: 0; right: 0; height: 2px;
    background: linear-gradient(90deg, #1f6feb, #58a6ff, #79c0ff, #1f6feb);
}
.hero-title {
    font-size: 28px; font-weight: 700;
    color: #e6edf3 !important;
    margin: 0 0 6px 0;
    letter-spacing: -0.5px;
}
.hero-sub {
    font-size: 14px; color: #8b949e !important;
    margin: 0;
}
.hero-pills { margin-top: 14px; display: flex; gap: 8px; flex-wrap: wrap; }
.pill {
    display: inline-flex; align-items: center; gap: 6px;
    background: #21262d; border: 1px solid #30363d;
    border-radius: 20px; padding: 4px 12px;
    font-size: 12px; color: #8b949e !important;
    font-weight: 500;
}
.pill-live { border-color: #238636; color: #3fb950 !important; background: #0f2a14; }

/* ── Metric cards ── */
.metrics-row { display: flex; gap: 12px; margin-bottom: 20px; }
.metric-card {
    flex: 1;
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 10px;
    padding: 16px 20px;
    text-align: center;
}
.metric-card.critical { border-color: #da3633; background: #1a0a0a; }
.metric-card.high     { border-color: #d29922; background: #1a1400; }
.metric-card.medium   { border-color: #1f6feb; background: #0a1628; }
.metric-card.good     { border-color: #238636; background: #0a1f0a; }
.metric-num {
    font-size: 36px; font-weight: 700; line-height: 1;
    margin-bottom: 4px;
}
.metric-num.red    { color: #f85149 !important; }
.metric-num.yellow { color: #e3b341 !important; }
.metric-num.blue   { color: #58a6ff !important; }
.metric-num.green  { color: #3fb950 !important; }
.metric-label { font-size: 11px; color: #8b949e !important; text-transform: uppercase; letter-spacing: 0.8px; }

/* ── Severity badges ── */
.badge {
    display: inline-block; border-radius: 4px;
    padding: 2px 8px; font-size: 11px; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.5px;
}
.badge-critical { background: #da3633; color: #fff !important; }
.badge-high     { background: #d29922; color: #0d1117 !important; }
.badge-medium   { background: #1f6feb; color: #fff !important; }
.badge-low      { background: #30363d; color: #8b949e !important; }

/* ── Issue cards ── */
.issue-card {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 14px 16px;
    margin-bottom: 8px;
}
.issue-card.critical { border-left: 3px solid #f85149; }
.issue-card.high     { border-left: 3px solid #e3b341; }
.issue-card.medium   { border-left: 3px solid #58a6ff; }
.issue-card.low      { border-left: 3px solid #30363d; }
.issue-title { font-size: 14px; font-weight: 600; color: #e6edf3 !important; margin-bottom: 4px; }
.issue-desc  { font-size: 13px; color: #8b949e !important; margin: 0; }
.issue-type  { font-size: 10px; color: #8b949e !important; text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 6px; }

/* ── Suggestion cards ── */
.suggestion-card {
    background: #0a1628;
    border: 1px solid #1f6feb44;
    border-left: 3px solid #58a6ff;
    border-radius: 8px;
    padding: 14px 16px;
    margin-bottom: 8px;
}
.suggestion-title { font-size: 14px; font-weight: 600; color: #79c0ff !important; margin-bottom: 4px; }
.suggestion-desc  { font-size: 13px; color: #8b949e !important; margin: 0; }

/* ── Agent chat ── */
.chat-agent {
    background: #161b22;
    border: 1px solid #30363d;
    border-left: 3px solid #58a6ff;
    border-radius: 8px;
    padding: 14px 16px;
    margin-bottom: 10px;
}
.chat-user {
    background: #0f2a14;
    border: 1px solid #238636;
    border-left: 3px solid #3fb950;
    border-radius: 8px;
    padding: 14px 16px;
    margin-bottom: 10px;
}
.chat-label { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 8px; }
.chat-label-agent { color: #58a6ff !important; }
.chat-label-user  { color: #3fb950 !important; }
.chat-text { font-size: 14px; color: #c9d1d9 !important; line-height: 1.6; }

/* ── Status bar ── */
.status-bar {
    background: #161b22;
    border: 1px solid #30363d;
    border-radius: 8px;
    padding: 12px 16px;
    margin-bottom: 16px;
    display: flex;
    align-items: center;
    gap: 12px;
}
.status-dot {
    width: 8px; height: 8px; border-radius: 50%;
    display: inline-block;
}
.status-dot-idle    { background: #8b949e; }
.status-dot-running { background: #3fb950; box-shadow: 0 0 8px #3fb950; animation: pulse 1.5s infinite; }
.status-dot-done    { background: #58a6ff; }
.status-dot-error   { background: #f85149; }
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }
.status-text { font-size: 13px; color: #c9d1d9 !important; }

/* ── Section headers ── */
.section-header {
    font-size: 11px; font-weight: 700; text-transform: uppercase;
    letter-spacing: 1px; color: #8b949e !important;
    border-bottom: 1px solid #21262d;
    padding-bottom: 8px; margin-bottom: 14px;
}

/* ── Tab styling ── */
[data-baseweb="tab-list"] { background: #161b22 !important; border-radius: 8px; }
[data-baseweb="tab"] { color: #8b949e !important; }
[aria-selected="true"] { color: #e6edf3 !important; }

/* ── Buttons ── */
.stButton > button {
    background: #238636 !important;
    border: 1px solid #2ea043 !important;
    color: #fff !important;
    font-weight: 600 !important;
    border-radius: 6px !important;
}
.stButton > button:hover {
    background: #2ea043 !important;
}

/* ── Inputs ── */
.stTextInput input, .stTextArea textarea {
    background: #0d1117 !important;
    border: 1px solid #30363d !important;
    color: #e6edf3 !important;
    border-radius: 6px !important;
}

/* ── Code blocks ── */
.stCode { background: #161b22 !important; }

/* ── Divider ── */
hr { border-color: #21262d !important; }

/* ── Expander ── */
[data-testid="stExpander"] {
    background: #161b22 !important;
    border: 1px solid #30363d !important;
    border-radius: 8px !important;
}

/* ── Download button ── */
[data-testid="stDownloadButton"] button {
    background: #21262d !important;
    border: 1px solid #30363d !important;
    color: #c9d1d9 !important;
}
</style>
""", unsafe_allow_html=True)

# ── Session state ──────────────────────────────────────────────────────────────

for key, default in [
    ("conversation", []),
    ("run_result", None),
    ("running", False),
    ("agent_status", "idle"),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ── Helpers ────────────────────────────────────────────────────────────────────

def get_report_files() -> list[Path]:
    if not REPORTS_DIR.exists():
        return []
    return sorted(REPORTS_DIR.glob("run_*.md"), key=lambda p: p.stat().st_mtime, reverse=True)


def severity_badge(severity: str) -> str:
    s = severity.lower()
    cls = {"critical": "badge-critical", "high": "badge-high", "medium": "badge-medium"}.get(s, "badge-low")
    return f'<span class="badge {cls}">{severity}</span>'


def issue_card_html(f: ParsedFinding) -> str:
    sev = f.severity.lower() if f.severity else "low"
    type_label = {"bug": "🐛 Bug", "ux_issue": "⚠️ UX Issue", "suggestion": "💡 Suggestion"}.get(f.kind, f.kind)
    card_class = f"issue-card {sev}" if f.kind != "suggestion" else "suggestion-card"
    title_class = "issue-title" if f.kind != "suggestion" else "suggestion-title"
    desc_class = "issue-desc" if f.kind != "suggestion" else "suggestion-desc"

    badge = severity_badge(f.severity) if f.severity and f.kind != "suggestion" else ""

    return f"""
<div class="{card_class}">
  <div class="issue-type">{type_label} {badge}</div>
  <div class="{title_class}">{f.title}</div>
  <p class="{desc_class}">{f.description}</p>
</div>"""


def render_metrics(result: QARunResult) -> None:
    bugs = result.all_bugs
    ux = result.all_ux_issues
    sugg = result.all_suggestions
    critical = result.critical_count

    st.markdown(f"""
<div class="metrics-row">
  <div class="metric-card critical">
    <div class="metric-num red">{critical}</div>
    <div class="metric-label">Critical Bugs</div>
  </div>
  <div class="metric-card high">
    <div class="metric-num yellow">{len(bugs)}</div>
    <div class="metric-label">Total Bugs</div>
  </div>
  <div class="metric-card medium">
    <div class="metric-num blue">{len(ux)}</div>
    <div class="metric-label">UX Issues</div>
  </div>
  <div class="metric-card good">
    <div class="metric-num green">{len(sugg)}</div>
    <div class="metric-label">Suggestions</div>
  </div>
</div>""", unsafe_allow_html=True)


# ── Sidebar ────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown("""
<div style="display:flex;align-items:center;gap:10px;margin-bottom:4px">
  <span style="font-size:22px">🔬</span>
  <span style="font-size:18px;font-weight:700;color:#e6edf3">QA Commander</span>
</div>
<div style="font-size:12px;color:#8b949e;margin-bottom:20px">Powered by Gemini Live API</div>
""", unsafe_allow_html=True)

    st.markdown('<div class="section-header">⚙️ Configuration</div>', unsafe_allow_html=True)
    target_url = st.text_input("Target URL", value="https://example.com", key="target_url",
                               help="Enter the URL to audit")
    max_steps = st.slider("Audit depth (steps)", min_value=1, max_value=8, value=3, key="max_steps")

    st.markdown('<div class="section-header" style="margin-top:20px">🎙️ Voice Command</div>',
                unsafe_allow_html=True)
    st.caption("Record an instruction — the agent hears and acts on it")
    st.markdown(
        '<div style="font-size:11px;color:#e3b341;margin-bottom:6px">'
        '⚠️ Allow microphone access in your browser if prompted</div>',
        unsafe_allow_html=True,
    )
    try:
        audio_input = st.audio_input("Speak your test instruction", key="voice_cmd")
    except Exception:
        audio_input = None
        st.caption("🎙️ Mic unavailable — use text command below")

    st.markdown('<div class="section-header" style="margin-top:16px">⌨️ Text Command</div>',
                unsafe_allow_html=True)
    text_cmd = st.text_area(
        "Focus instruction",
        placeholder="e.g. Check navigation links and CTAs",
        key="text_cmd",
        height=72,
        label_visibility="collapsed",
    )

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    run_btn = st.button(
        "🚀 Run QA Audit" if not st.session_state.running else "⏳ Running…",
        type="primary",
        use_container_width=True,
        disabled=st.session_state.running,
    )

    if st.button("🗑️ Clear session", use_container_width=True):
        st.session_state.conversation = []
        st.session_state.run_result = None
        st.session_state.agent_status = "idle"
        st.rerun()

    st.markdown('<div class="section-header" style="margin-top:20px">📂 Run History</div>',
                unsafe_allow_html=True)
    report_files = get_report_files()
    selected_report_name = None
    if report_files:
        selected_report_name = st.selectbox(
            "Previous runs",
            [r.name for r in report_files],
            key="history_select",
            label_visibility="collapsed",
        )
    else:
        st.caption("No previous runs yet.")

# ── Hero ───────────────────────────────────────────────────────────────────────

status_map = {
    "idle":    ("status-dot-idle",    "Ready to audit"),
    "running": ("status-dot-running", "Agent running — analysing in real time…"),
    "done":    ("status-dot-done",    "Audit complete"),
    "error":   ("status-dot-error",   "Run ended with errors"),
}
dot_cls, status_text = status_map.get(st.session_state.agent_status, status_map["idle"])

st.markdown(f"""
<div class="hero">
  <div class="hero-title">QA Commander Live</div>
  <div class="hero-sub">Multimodal AI agent that sees interfaces, hears your commands, speaks findings, and creates bug reports</div>
  <div class="hero-pills">
    <span class="pill pill-live">● Live</span>
    <span class="pill">👁 Sees</span>
    <span class="pill">👂 Hears</span>
    <span class="pill">🔊 Speaks</span>
    <span class="pill">📋 Creates</span>
    <span class="pill" style="margin-left:auto">
      <span class="status-dot {dot_cls}"></span>
      <span>{status_text}</span>
    </span>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Run trigger ────────────────────────────────────────────────────────────────

if run_btn and not st.session_state.running:
    if not os.environ.get("GEMINI_API_KEY"):
        st.error("⚠️ GEMINI_API_KEY environment variable is not set.")
        st.stop()

    user_audio: bytes | None = None
    if audio_input is not None:
        try:
            audio_bytes = audio_input.read()
            user_audio = audio_bytes if audio_bytes else None
        except Exception:
            user_audio = None
    if user_audio:
        st.session_state.conversation.append({
            "role": "user",
            "content": "🎙️ Voice command recorded",
            "audio": user_audio,
        })
    elif text_cmd.strip():
        st.session_state.conversation.append({
            "role": "user",
            "content": f"⌨️ {text_cmd.strip()}",
        })

    st.session_state.running = True
    st.session_state.agent_status = "running"

    def on_turn_callback(step: int, record: StepRecord) -> None:
        st.session_state.conversation.append({
            "role": "agent",
            "step": step,
            "content": record.agent_narration,
            "status": record.status,
            "audio": record.audio_wav,
            "screenshot": record.screenshot,
            "findings": record.findings,
        })

    with st.spinner("🔬 QA Commander is auditing — see · hear · speak · create…"):
        result = run_live_agent(
            target_url=target_url,
            max_steps=max_steps,
            user_audio=user_audio,
            user_text=text_cmd.strip() or None,
            on_turn=on_turn_callback,
            headless=True,
        )

    st.session_state.run_result = result
    st.session_state.running = False
    st.session_state.agent_status = "done" if result.success else "error"
    st.rerun()

# ── Load active result ─────────────────────────────────────────────────────────

result: QARunResult | None = st.session_state.run_result

# ── Metrics bar (when result available) ───────────────────────────────────────

if result is not None:
    render_metrics(result)

# ── Tabs ───────────────────────────────────────────────────────────────────────

tab_issues, tab_conv, tab_screenshots, tab_report = st.tabs([
    "🐛 Issues & Suggestions",
    "🤖 Agent Live Feed",
    "📸 Screenshots",
    "📄 Full Report",
])

# ══════════════════════════════════════════════════════════════════════════════
# Tab 1 — Issues & Suggestions (the main value)
# ══════════════════════════════════════════════════════════════════════════════

with tab_issues:
    if result is None:
        st.markdown("""
<div style="text-align:center;padding:60px 0;color:#8b949e">
  <div style="font-size:48px;margin-bottom:16px">🔬</div>
  <div style="font-size:18px;font-weight:600;color:#c9d1d9;margin-bottom:8px">No audit results yet</div>
  <div style="font-size:14px">Enter a URL and click <strong>Run QA Audit</strong> to begin</div>
</div>""", unsafe_allow_html=True)
    else:
        bugs = result.all_bugs
        ux_issues = result.all_ux_issues
        suggestions = result.all_suggestions

        # Two-column layout: bugs + ux issues | suggestions
        col_left, col_right = st.columns([3, 2])

        with col_left:
            if bugs:
                st.markdown('<div class="section-header">🐛 Bugs Found</div>', unsafe_allow_html=True)
                # Sort by severity
                severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
                for f in sorted(bugs, key=lambda x: severity_order.get(x.severity.lower(), 4)):
                    st.markdown(issue_card_html(f), unsafe_allow_html=True)
            else:
                st.markdown("""
<div style="background:#0f2a14;border:1px solid #238636;border-radius:8px;padding:16px;margin-bottom:16px">
  <span style="color:#3fb950;font-weight:600">✅ No bugs detected in this audit pass</span>
</div>""", unsafe_allow_html=True)

            if ux_issues:
                st.markdown('<div class="section-header" style="margin-top:20px">⚠️ UX Issues</div>',
                            unsafe_allow_html=True)
                for f in sorted(ux_issues, key=lambda x: severity_order.get(x.severity.lower(), 4)):
                    st.markdown(issue_card_html(f), unsafe_allow_html=True)

        with col_right:
            if suggestions:
                st.markdown('<div class="section-header">💡 UX Suggestions</div>', unsafe_allow_html=True)
                for f in suggestions:
                    st.markdown(f"""
<div class="suggestion-card">
  <div class="suggestion-title">💡 {f.title}</div>
  <p class="suggestion-desc">{f.description}</p>
</div>""", unsafe_allow_html=True)
            else:
                st.markdown('<div class="section-header">💡 UX Suggestions</div>', unsafe_allow_html=True)
                st.caption("Suggestions will appear after the audit.")

            # Step-level summary timeline
            if result.steps:
                st.markdown('<div class="section-header" style="margin-top:24px">⏱ Audit Timeline</div>',
                            unsafe_allow_html=True)
                for step in result.steps:
                    icon = {"PASS": "✅", "WARNING": "⚠️", "FAIL": "❌", "DONE": "🏁", "STOPPED": "🛑"}.get(
                        step.status, "❓"
                    )
                    bugs_in_step = len([f for f in step.findings if f.kind == "bug"])
                    ux_in_step = len([f for f in step.findings if f.kind == "ux_issue"])
                    st.markdown(f"""
<div style="background:#161b22;border:1px solid #30363d;border-radius:6px;padding:10px 14px;margin-bottom:6px;display:flex;justify-content:space-between;align-items:center">
  <span style="color:#e6edf3;font-size:13px">{icon} Step {step.step}
    {'<span style="color:#8b949e;font-size:12px"> · '+step.click_target+'</span>' if step.click_target else ''}
  </span>
  <span style="font-size:12px;color:#8b949e">{bugs_in_step}B · {ux_in_step}UX</span>
</div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# Tab 2 — Agent Live Feed
# ══════════════════════════════════════════════════════════════════════════════

with tab_conv:
    if not st.session_state.conversation:
        st.markdown("""
<div style="text-align:center;padding:60px 0;color:#8b949e">
  <div style="font-size:48px;margin-bottom:16px">🤖</div>
  <div style="font-size:18px;font-weight:600;color:#c9d1d9;margin-bottom:8px">Agent conversation will appear here</div>
  <div style="font-size:14px">The agent narrates every step as it audits your interface</div>
</div>""", unsafe_allow_html=True)
    else:
        for msg in st.session_state.conversation:
            if msg["role"] == "user":
                st.markdown(f"""
<div class="chat-user">
  <div class="chat-label chat-label-user">👤 Tester</div>
  <div class="chat-text">{msg["content"]}</div>
</div>""", unsafe_allow_html=True)
                if msg.get("audio"):
                    st.audio(msg["audio"], format="audio/wav")
            else:
                step_num = msg.get("step", "")
                status = msg.get("status", "")
                status_icon = {"PASS": "✅", "WARNING": "⚠️", "FAIL": "❌", "DONE": "🏁"}.get(status, "")
                findings: list[ParsedFinding] = msg.get("findings", [])
                bug_count = len([f for f in findings if f.kind == "bug"])
                ux_count = len([f for f in findings if f.kind == "ux_issue"])

                st.markdown(f"""
<div class="chat-agent">
  <div class="chat-label chat-label-agent">
    🤖 Agent — Step {step_num} &nbsp; {status_icon}
    {'<span style="font-size:11px;color:#f85149;margin-left:8px">'+str(bug_count)+' bugs</span>' if bug_count else ''}
    {'<span style="font-size:11px;color:#e3b341;margin-left:6px">'+str(ux_count)+' UX</span>' if ux_count else ''}
  </div>
  <div class="chat-text">{msg.get("content", "")}</div>
</div>""", unsafe_allow_html=True)
                if msg.get("audio"):
                    st.audio(msg["audio"], format="audio/wav")

# ══════════════════════════════════════════════════════════════════════════════
# Tab 3 — Screenshots
# ══════════════════════════════════════════════════════════════════════════════

with tab_screenshots:
    screenshots: list[Path] = []
    if result is not None:
        screenshots = result.screenshots
    elif selected_report_name:
        run_id = selected_report_name.replace("run_", "").replace(".md", "")
        run_dir = SCREENSHOTS_DIR / f"run_{run_id}"
        if run_dir.exists():
            screenshots = sorted(run_dir.glob("step_*.png"), key=lambda p: p.name)

    if screenshots:
        st.markdown(f'<div class="section-header">{len(screenshots)} screenshots captured</div>',
                    unsafe_allow_html=True)
        cols = st.columns(min(3, len(screenshots)))
        for i, shot in enumerate(screenshots):
            with cols[i % len(cols)]:
                st.image(str(shot), caption=f"Step {i+1}", use_container_width=True)
    else:
        st.markdown("""
<div style="text-align:center;padding:60px 0;color:#8b949e">
  <div style="font-size:48px;margin-bottom:16px">📸</div>
  <div style="font-size:14px">Screenshots appear here after an audit run</div>
</div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# Tab 4 — Full Report
# ══════════════════════════════════════════════════════════════════════════════

with tab_report:
    report_path: Path | None = None

    if result is not None and result.md_report_path.exists():
        report_path = result.md_report_path
    elif selected_report_name:
        candidate = REPORTS_DIR / selected_report_name
        if candidate.exists():
            report_path = candidate

    if report_path:
        report_text = report_path.read_text(encoding="utf-8")
        col_dl, _ = st.columns([1, 4])
        with col_dl:
            st.download_button(
                "⬇️ Download .md",
                data=report_text,
                file_name=report_path.name,
                mime="text/markdown",
            )
        st.markdown(report_text)
    else:
        st.markdown("""
<div style="text-align:center;padding:60px 0;color:#8b949e">
  <div style="font-size:48px;margin-bottom:16px">📄</div>
  <div style="font-size:14px">The full Markdown report will appear here after an audit run</div>
</div>""", unsafe_allow_html=True)
