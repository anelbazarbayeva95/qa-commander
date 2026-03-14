"""QA Commander Live — Streamlit UI."""

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

SUGGESTED_PROMPTS = [
    "Check all navigation links and CTAs work correctly",
    "Audit accessibility: contrast, labels, focus indicators",
    "Identify bad design patterns and layout issues",
    "Test the checkout or signup flow end-to-end",
]

# ── Page config ────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="QA Commander",
    page_icon="⬡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ────────────────────────────────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}
#MainMenu, footer, header { visibility: hidden; }

.stApp { background: #f1f5f9; }

/* ── Sidebar dark navy ── */
[data-testid="stSidebar"] { background: #0f1e2e !important; border-right: none; }
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] div { color: #94a3b8 !important; }
[data-testid="stSidebar"] strong,
[data-testid="stSidebar"] b { color: #cbd5e1 !important; }
[data-testid="stSidebar"] input,
[data-testid="stSidebar"] textarea {
    background: #1e3045 !important;
    border: 1px solid #2d4a6a !important;
    color: #e2e8f0 !important;
    border-radius: 6px !important;
}
[data-testid="stSidebar"] .stSelectbox > div > div {
    background: #1e3045 !important; border-color: #2d4a6a !important; color: #e2e8f0 !important;
}
[data-testid="stSidebar"] hr { border-color: #1a3050 !important; }
[data-testid="stSidebar"] .stButton > button {
    border-radius: 8px !important; font-weight: 600 !important; font-size: 13px !important;
    border: none !important;
}
[data-testid="stSidebar"] .stButton:first-of-type > button {
    background: #2563eb !important; color: #fff !important;
}
[data-testid="stSidebar"] .stButton:last-of-type > button {
    background: #1e3045 !important; color: #94a3b8 !important;
}

/* ── Cards ── */
.card {
    background: #fff; border-radius: 12px; padding: 20px 24px;
    border: 1px solid #e2e8f0;
    box-shadow: 0 1px 3px rgba(0,0,0,.05);
    margin-bottom: 12px;
}

/* ── Metric card ── */
.metric-card {
    background: #fff; border-radius: 12px; padding: 20px 22px;
    border: 1px solid #e2e8f0; box-shadow: 0 1px 3px rgba(0,0,0,.05);
}
.metric-val  { font-size: 34px; font-weight: 700; line-height: 1; letter-spacing: -.02em; }
.metric-lbl  { font-size: 11px; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: .07em; margin-top: 5px; }
.metric-sub  { font-size: 12px; color: #94a3b8; margin-top: 3px; }

/* ── Agent status banner ── */
.agent-status {
    background: #eff6ff; border: 1px solid #bfdbfe; border-radius: 10px;
    padding: 14px 20px; margin-bottom: 16px; display: flex; align-items: center; gap: 12px;
}
.agent-status-dot {
    width: 8px; height: 8px; border-radius: 50%; background: #2563eb;
    animation: pulse 1.4s ease-in-out infinite;
    flex-shrink: 0;
}
@keyframes pulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50%       { opacity: .4; transform: scale(.8); }
}
.agent-status-text { font-size: 13px; font-weight: 500; color: #1e40af; }

/* ── Step timeline ── */
.step-timeline { display: flex; gap: 8px; align-items: center; margin: 16px 0; flex-wrap: wrap; }
.step-dot {
    width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center;
    justify-content: center; font-size: 11px; font-weight: 700; flex-shrink: 0;
}
.step-dot-pass    { background: #dcfce7; color: #166534; }
.step-dot-warning { background: #fef9c3; color: #854d0e; }
.step-dot-fail    { background: #fee2e2; color: #991b1b; }
.step-dot-done    { background: #dbeafe; color: #1e40af; }
.step-dot-stopped { background: #f1f5f9; color: #64748b; }
.step-dot-active  { background: #2563eb; color: #fff; }
.step-connector   { height: 2px; flex: 1; min-width: 16px; background: #e2e8f0; }

/* ── Finding rows ── */
.finding-row {
    background: #fff; border-radius: 10px; padding: 14px 18px;
    margin: 7px 0; border: 1px solid #e2e8f0;
    box-shadow: 0 1px 2px rgba(0,0,0,.03);
}
.finding-row-critical { border-left: 4px solid #dc2626; }
.finding-row-high     { border-left: 4px solid #ea580c; }
.finding-row-medium   { border-left: 4px solid #d97706; }
.finding-row-low      { border-left: 4px solid #94a3b8; }
.finding-row-ux       { border-left: 4px solid #2563eb; }
.finding-row-suggest  { border-left: 4px solid #059669; }
.finding-row-dismissed { opacity: .4; }

.finding-title { font-size: 14px; font-weight: 600; color: #111827; }
.finding-desc  { font-size: 13px; color: #6b7280; margin-top: 4px; line-height: 1.55; }

/* ── Pills ── */
.pill {
    display: inline-block; padding: 2px 9px; border-radius: 20px;
    font-size: 11px; font-weight: 600; letter-spacing: .04em;
    text-transform: uppercase; margin-left: 7px; vertical-align: middle;
}
.pill-critical { background: #fee2e2; color: #991b1b; }
.pill-high     { background: #ffedd5; color: #9a3412; }
.pill-medium   { background: #fef3c7; color: #92400e; }
.pill-low      { background: #f1f5f9; color: #475569; }
.pill-confirmed{ background: #dcfce7; color: #166534; }
.pill-dismissed{ background: #f1f5f9; color: #94a3b8; }

/* ── Chip ── */
.chip { display: inline-block; padding: 3px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; }
.chip-pass    { background: #dcfce7; color: #166534; }
.chip-warning { background: #fef9c3; color: #854d0e; }
.chip-fail    { background: #fee2e2; color: #991b1b; }
.chip-done    { background: #dbeafe; color: #1e40af; }
.chip-stopped { background: #f1f5f9; color: #475569; }

/* ── Turn card ── */
.turn-card {
    background: #fff; border-radius: 10px; border: 1px solid #e2e8f0;
    padding: 16px 20px; margin: 8px 0; box-shadow: 0 1px 2px rgba(0,0,0,.03);
}

/* ── Section heading ── */
.sec-head {
    font-size: 11px; font-weight: 700; letter-spacing: .09em;
    text-transform: uppercase; color: #94a3b8; margin: 20px 0 10px 0;
}

/* ── Suggested prompt ── */
.prompt-chip {
    display: inline-block; background: #fff; border: 1px solid #e2e8f0;
    border-radius: 20px; padding: 6px 14px; font-size: 13px; color: #374151;
    cursor: pointer; margin: 4px; box-shadow: 0 1px 2px rgba(0,0,0,.04);
    transition: border-color .15s;
}
.prompt-chip:hover { border-color: #2563eb; color: #2563eb; }

/* Tabs */
.stTabs [data-baseweb="tab-list"] { background: transparent; gap: 0; border-bottom: 2px solid #e2e8f0; }
.stTabs [data-baseweb="tab"] { background: transparent; border: none; color: #64748b; font-size: 13px; font-weight: 500; padding: 10px 20px; }
.stTabs [aria-selected="true"] { color: #2563eb !important; border-bottom: 2px solid #2563eb !important; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

# ── Session state ───────────────────────────────────────────────────────────────

defaults = {
    "conversation": [],
    "run_result": None,
    "running": False,
    "latest_run_id": None,
    "agent_log": [],          # real-time step log during run
    "dismissed": set(),       # set of finding keys dismissed by user
    "confirmed": set(),       # set of finding keys confirmed by user
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── Helpers ────────────────────────────────────────────────────────────────────

def get_report_files() -> list[Path]:
    if not REPORTS_DIR.exists():
        return []
    return sorted(REPORTS_DIR.glob("run_*.md"), key=lambda p: p.stat().st_mtime, reverse=True)


def finding_key(f: ParsedFinding) -> str:
    return f"{f.kind}:{f.title}"


def severity_pill_html(severity: str) -> str:
    s = severity.lower()
    cls = {"critical": "pill-critical", "high": "pill-high", "medium": "pill-medium"}.get(s, "pill-low")
    return f'<span class="pill {cls}">{severity}</span>'


def status_chip_html(status: str) -> str:
    cls = {"PASS": "chip-pass", "WARNING": "chip-warning", "FAIL": "chip-fail",
           "DONE": "chip-done", "STOPPED": "chip-stopped"}.get(status, "chip-stopped")
    label = {"PASS": "Pass", "WARNING": "Warning", "FAIL": "Fail",
             "DONE": "Done", "STOPPED": "Stopped"}.get(status, status)
    return f'<span class="chip {cls}">{label}</span>'


def finding_row_html(f: ParsedFinding, extra_class: str = "") -> str:
    if f.kind == "bug":
        sev = f.severity.lower()
        row_cls = f"finding-row finding-row-{sev}" if sev in ("critical", "high", "medium") else "finding-row finding-row-low"
        pill = severity_pill_html(f.severity)
    elif f.kind == "ux_issue":
        row_cls = "finding-row finding-row-ux"
        pill = severity_pill_html(f.severity) if f.severity else ""
    else:
        row_cls = "finding-row finding-row-suggest"
        pill = ""
    if extra_class:
        row_cls += f" {extra_class}"
    return (
        f'<div class="{row_cls}">'
        f'<div class="finding-title">{f.title}{pill}</div>'
        f'<div class="finding-desc">{f.description}</div>'
        f'</div>'
    )


def render_finding_with_actions(f: ParsedFinding) -> None:
    """Render a finding card with Confirm / Dismiss actions."""
    key = finding_key(f)
    is_dismissed = key in st.session_state.dismissed
    is_confirmed = key in st.session_state.confirmed

    extra = "finding-row-dismissed" if is_dismissed else ""
    st.markdown(finding_row_html(f, extra), unsafe_allow_html=True)

    col_a, col_b, col_c = st.columns([1, 1, 8])
    if is_confirmed:
        col_a.markdown('<span class="pill pill-confirmed">✓ Confirmed</span>', unsafe_allow_html=True)
    else:
        if col_a.button("✓ Confirm", key=f"confirm_{key}", help="Mark as a real issue"):
            st.session_state.confirmed.add(key)
            st.session_state.dismissed.discard(key)
            st.rerun()

    if is_dismissed:
        col_b.markdown('<span class="pill pill-dismissed">Dismissed</span>', unsafe_allow_html=True)
    else:
        if col_b.button("✕ Dismiss", key=f"dismiss_{key}", help="Mark as not relevant"):
            st.session_state.dismissed.add(key)
            st.session_state.confirmed.discard(key)
            st.rerun()


# ── Sidebar ────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown(
        '<div style="padding:8px 0 18px 0">'
        '<div style="font-size:19px;font-weight:700;color:#f8fafc;letter-spacing:-.02em">QA Commander</div>'
        '<div style="font-size:11px;color:#475569;margin-top:3px">Gemini Live · Multimodal Agent</div>'
        '</div>',
        unsafe_allow_html=True,
    )
    st.divider()

    st.markdown("**Target URL**")
    target_url = st.text_input("URL", value="https://example.com", key="target_url", label_visibility="collapsed")

    st.markdown("**Audit depth**")
    max_steps = st.slider("Steps", 1, 8, 3, key="max_steps", label_visibility="collapsed")
    st.caption(f"{max_steps} interaction step{'s' if max_steps != 1 else ''}")

    st.divider()
    st.markdown("**Voice command**")
    try:
        audio_input = st.audio_input("Record", key="voice_cmd", label_visibility="collapsed")
    except Exception:
        audio_input = None
        st.caption("Microphone unavailable — use text below")

    st.markdown("**Text instruction**")
    text_cmd = st.text_area(
        "Instruction", placeholder="e.g. Check all navigation links work",
        key="text_cmd", height=72, label_visibility="collapsed",
    )

    st.divider()
    run_btn = st.button("Run QA Agent", type="primary", use_container_width=True, disabled=st.session_state.running)
    if st.button("Clear session", use_container_width=True):
        for k in ("conversation", "agent_log", "dismissed", "confirmed"):
            st.session_state[k] = [] if k != "dismissed" and k != "confirmed" else set()
        st.session_state.run_result = None
        st.session_state.latest_run_id = None
        st.rerun()

    st.divider()
    st.markdown("**Run history**")
    report_files = get_report_files()
    if report_files:
        default_idx = 0
        if st.session_state.latest_run_id:
            latest_name = f"run_{st.session_state.latest_run_id}.md"
            names = [r.name for r in report_files]
            if latest_name in names:
                default_idx = names.index(latest_name)
        selected_report_name = st.selectbox(
            "History", [r.name for r in report_files],
            index=default_idx, key="history_select", label_visibility="collapsed",
        )
    else:
        st.caption("No runs yet.")
        selected_report_name = None

# ── Run trigger ────────────────────────────────────────────────────────────────

if run_btn and not st.session_state.running:
    if not os.environ.get("GEMINI_API_KEY"):
        st.error("GEMINI_API_KEY is not set.")
    else:
        user_audio: bytes | None = None
        if audio_input is not None:
            try:
                user_audio = audio_input.read() or None
            except Exception:
                user_audio = None

        if user_audio:
            st.session_state.conversation.append({"role": "user", "content": "Voice command recorded", "audio": user_audio})
        elif text_cmd.strip():
            st.session_state.conversation.append({"role": "user", "content": text_cmd.strip()})

        st.session_state.running = True
        st.session_state.agent_log = []

        def on_turn_callback(step: int, record: StepRecord) -> None:
            st.session_state.agent_log.append(
                f"Step {step} — {record.status} — clicked: {record.click_target or 'none'}"
            )
            st.session_state.conversation.append({
                "role": "agent", "step": step,
                "content": record.agent_narration,
                "status": record.status,
                "audio": record.audio_wav,
                "screenshot": record.screenshot,
                "findings": record.findings,
            })

        with st.status("Agent is running…", expanded=True) as status_box:
            st.write(f"Opening browser → {target_url}")
            result = run_live_agent(
                target_url=target_url,
                max_steps=max_steps,
                user_audio=user_audio,
                user_text=text_cmd.strip() or None,
                on_turn=on_turn_callback,
                headless=True,
            )
            for log_line in st.session_state.agent_log:
                st.write(log_line)
            if result.success:
                status_box.update(label="Audit complete", state="complete", expanded=False)
            else:
                status_box.update(label=f"Audit failed: {result.error_message}", state="error", expanded=True)

        st.session_state.run_result = result
        st.session_state.latest_run_id = result.run_id
        st.session_state.running = False
        st.rerun()

# ── Page header ────────────────────────────────────────────────────────────────

result: QARunResult | None = st.session_state.run_result

st.markdown(
    '<div class="card" style="margin-bottom:20px;padding:16px 24px">'
    '<div style="display:flex;align-items:center;justify-content:space-between">'
    '<div>'
    '<div style="font-size:21px;font-weight:700;color:#0f172a;letter-spacing:-.02em">QA Commander</div>'
    '<div style="font-size:13px;color:#64748b;margin-top:2px">'
    'Autonomous QA &amp; UX audit — Gemini Live multimodal agent'
    '</div></div>'
    '</div></div>',
    unsafe_allow_html=True,
)

# ── Metric row ─────────────────────────────────────────────────────────────────

if result:
    bugs = result.all_bugs
    ux_issues = result.all_ux_issues
    suggestions = result.all_suggestions
    critical = result.critical_count
    summ = result.summary
    pass_pct = int(summ["pass"] / summ["total"] * 100) if summ["total"] > 0 else 0

    c1, c2, c3, c4, c5 = st.columns(5)
    metrics = [
        (c1, critical,          "#dc2626", "Critical",    "Severity: Critical"),
        (c2, len(bugs),         "#ea580c", "Bugs",        "All severities"),
        (c3, len(ux_issues),    "#2563eb", "UX Issues",   "Design & usability"),
        (c4, len(suggestions),  "#059669", "Suggestions", "Improvements"),
        (c5, f"{pass_pct}%",    "#059669" if pass_pct >= 80 else "#d97706" if pass_pct >= 50 else "#dc2626",
             "Steps Passed", f"{summ['pass']} of {summ['total']} steps"),
    ]
    for col, val, color, label, sub in metrics:
        with col:
            st.markdown(
                f'<div class="metric-card"><div class="metric-val" style="color:{color}">{val}</div>'
                f'<div class="metric-lbl">{label}</div><div class="metric-sub">{sub}</div></div>',
                unsafe_allow_html=True,
            )

    # Step timeline
    st.markdown('<div class="sec-head">Audit trail</div>', unsafe_allow_html=True)
    timeline_html = '<div class="step-timeline">'
    dot_cls = {"PASS": "step-dot-pass", "WARNING": "step-dot-warning", "FAIL": "step-dot-fail",
               "DONE": "step-dot-done", "STOPPED": "step-dot-stopped"}
    for i, step in enumerate(result.steps):
        cls = dot_cls.get(step.status, "step-dot-stopped")
        timeline_html += f'<div class="step-dot {cls}" title="Step {step.step}: {step.status}">{step.step}</div>'
        if i < len(result.steps) - 1:
            timeline_html += '<div class="step-connector"></div>'
    timeline_html += "</div>"
    st.markdown(timeline_html, unsafe_allow_html=True)
    st.markdown("<div style='margin-bottom:8px'></div>", unsafe_allow_html=True)

else:
    # ── Ready state with suggested prompts ──
    st.markdown(
        '<div class="card" style="text-align:center;padding:32px 24px">'
        '<div style="font-size:15px;font-weight:600;color:#374151;margin-bottom:6px">Ready to audit</div>'
        '<div style="font-size:13px;color:#94a3b8;margin-bottom:20px">'
        'Enter a URL in the sidebar, optionally record a voice command, then click Run QA Agent.'
        '</div>'
        '<div style="font-size:12px;font-weight:600;color:#64748b;text-transform:uppercase;letter-spacing:.07em;margin-bottom:10px">'
        'Suggested focus areas'
        '</div>'
        + "".join(f'<span class="prompt-chip">{p}</span>' for p in SUGGESTED_PROMPTS)
        + '</div>',
        unsafe_allow_html=True,
    )

# ── Tabs ───────────────────────────────────────────────────────────────────────

tab_findings, tab_feed, tab_steps, tab_report, tab_screenshots = st.tabs(
    ["Findings", "Live Feed", "Step Details", "Report", "Screenshots"]
)

# ── Tab 1: Findings ─────────────────────────────────────────────────────────────

with tab_findings:
    if result is None:
        st.markdown('<div style="color:#9ca3af;font-size:14px;padding:16px 0">No findings yet.</div>', unsafe_allow_html=True)
    else:
        bugs = result.all_bugs
        ux_issues = result.all_ux_issues
        suggestions = result.all_suggestions
        sev_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}

        total_findings = len(bugs) + len(ux_issues) + len(suggestions)
        confirmed_count = sum(1 for f in result.all_findings if finding_key(f) in st.session_state.confirmed)
        dismissed_count = sum(1 for f in result.all_findings if finding_key(f) in st.session_state.dismissed)

        if total_findings:
            st.markdown(
                f'<div style="font-size:13px;color:#64748b;margin-bottom:12px">'
                f'{total_findings} finding{"s" if total_findings != 1 else ""} · '
                f'<span style="color:#166534">{confirmed_count} confirmed</span> · '
                f'<span style="color:#94a3b8">{dismissed_count} dismissed</span>'
                f'</div>',
                unsafe_allow_html=True,
            )

        if bugs:
            st.markdown('<div class="sec-head">Bugs</div>', unsafe_allow_html=True)
            for f in sorted(bugs, key=lambda x: sev_order.get(x.severity.lower(), 9)):
                render_finding_with_actions(f)

        if ux_issues:
            st.markdown('<div class="sec-head">UX & Design Issues</div>', unsafe_allow_html=True)
            for f in ux_issues:
                render_finding_with_actions(f)

        if suggestions:
            st.markdown('<div class="sec-head">Suggestions</div>', unsafe_allow_html=True)
            for f in suggestions:
                render_finding_with_actions(f)

        if not total_findings:
            st.markdown(
                '<div style="color:#9ca3af;font-size:14px;padding:16px 0">'
                'No structured findings — check Live Feed for agent narration.</div>',
                unsafe_allow_html=True,
            )

# ── Tab 2: Live Feed ────────────────────────────────────────────────────────────

with tab_feed:
    if not st.session_state.conversation:
        st.markdown('<div style="color:#9ca3af;font-size:14px;padding:16px 0">Run the agent to see the live conversation.</div>', unsafe_allow_html=True)
    else:
        for msg in st.session_state.conversation:
            if msg["role"] == "user":
                st.markdown(
                    f'<div class="turn-card" style="border-left:4px solid #059669">'
                    f'<div style="font-size:11px;font-weight:700;color:#059669;letter-spacing:.07em;'
                    f'text-transform:uppercase;margin-bottom:6px">Tester</div>'
                    f'<div style="font-size:14px;color:#374151;line-height:1.6">{msg["content"]}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                if msg.get("audio"):
                    st.audio(msg["audio"], format="audio/wav")
            else:
                step = msg.get("step", "")
                chip = status_chip_html(msg.get("status", ""))
                narration = msg.get("content", "")
                step_findings: list[ParsedFinding] = msg.get("findings", [])
                st.markdown(
                    f'<div class="turn-card" style="border-left:4px solid #2563eb">'
                    f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:8px">'
                    f'<span style="font-size:11px;font-weight:700;color:#2563eb;letter-spacing:.07em;'
                    f'text-transform:uppercase">Step {step}</span>{chip}'
                    f'</div>'
                    f'<div style="font-size:14px;color:#374151;line-height:1.6">{narration}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                if msg.get("audio"):
                    st.audio(msg["audio"], format="audio/wav")
                if step_findings:
                    with st.expander(f"View {len(step_findings)} finding(s) from this step"):
                        for f in step_findings:
                            st.markdown(finding_row_html(f), unsafe_allow_html=True)

# ── Tab 3: Step Details ─────────────────────────────────────────────────────────

with tab_steps:
    if result is None:
        st.markdown('<div style="color:#9ca3af;font-size:14px;padding:16px 0">No run data yet.</div>', unsafe_allow_html=True)
    else:
        for step in result.steps:
            icon = {"PASS": "✅", "WARNING": "⚠️", "FAIL": "❌", "DONE": "🏁", "STOPPED": "🛑"}.get(step.status, "❓")
            with st.expander(f"{icon} Step {step.step} · {step.status} · clicked: {step.click_target or 'none'}"):
                ca, cb = st.columns(2)
                ca.markdown(f"**Before URL**\n\n{step.before_url}")
                cb.markdown(f"**After URL**\n\n{step.after_url}")

                if step.agent_narration:
                    st.markdown("**Agent reasoning**")
                    st.markdown(
                        f'<div class="card" style="padding:14px 18px">'
                        f'<div style="font-size:14px;color:#374151;line-height:1.6">{step.agent_narration}</div>'
                        f'</div>',
                        unsafe_allow_html=True,
                    )

                cc, cd, ce = st.columns(3)
                cc.metric("Console errors", len(step.console_errors))
                cd.metric("Network failures", len(step.network_failures))
                ce.metric("Findings", len(step.findings))

                for flag in step.visual_flags:
                    st.warning(flag)
                if step.error:
                    st.error(step.error)
                if step.findings:
                    st.markdown("**Findings this step**")
                    for f in step.findings:
                        st.markdown(finding_row_html(f), unsafe_allow_html=True)

# ── Tab 4: Report ───────────────────────────────────────────────────────────────

with tab_report:
    report_to_show: Path | None = None
    if result is not None and result.md_report_path.exists():
        report_to_show = result.md_report_path
    elif selected_report_name:
        candidate = REPORTS_DIR / selected_report_name
        if candidate.exists():
            report_to_show = candidate

    if report_to_show:
        report_text = report_to_show.read_text(encoding="utf-8")
        st.download_button("Download report (.md)", data=report_text, file_name=report_to_show.name, mime="text/markdown")
        st.markdown(f'<div class="card">{report_text}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div style="color:#9ca3af;font-size:14px;padding:16px 0">No report yet.</div>', unsafe_allow_html=True)

# ── Tab 5: Screenshots ──────────────────────────────────────────────────────────

with tab_screenshots:
    screenshots: list[Path] = []
    if result is not None:
        screenshots = result.screenshots
    elif selected_report_name:
        run_id_str = selected_report_name.replace("run_", "").replace(".md", "")
        run_dir = SCREENSHOTS_DIR / f"run_{run_id_str}"
        if run_dir.exists():
            screenshots = sorted(run_dir.glob("step_*.png"), key=lambda p: p.name)

    if screenshots:
        cols = st.columns(min(3, len(screenshots)))
        for i, shot in enumerate(screenshots):
            with cols[i % len(cols)]:
                st.image(str(shot), caption=f"Step {i + 1}", use_container_width=True)
    else:
        st.markdown('<div style="color:#9ca3af;font-size:14px;padding:16px 0">Screenshots appear here after a run.</div>', unsafe_allow_html=True)
