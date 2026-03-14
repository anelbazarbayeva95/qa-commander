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

# ── Page config ────────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="QA Commander",
    page_icon="⬡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ─────────────────────────────────────────────────────────────────

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
}

#MainMenu { visibility: hidden; }
footer    { visibility: hidden; }
header    { visibility: hidden; }

/* Page background */
.stApp { background: #f1f5f9; }

/* Sidebar — dark navy like Lookback */
[data-testid="stSidebar"] {
    background: #0f1e2e !important;
    border-right: none;
}
[data-testid="stSidebar"] * { color: #cbd5e1 !important; }
[data-testid="stSidebar"] input,
[data-testid="stSidebar"] textarea {
    background: #1e3045 !important;
    border: 1px solid #2d4a6a !important;
    color: #e2e8f0 !important;
    border-radius: 6px !important;
}
[data-testid="stSidebar"] hr { border-color: #1e3045 !important; }
[data-testid="stSidebar"] label {
    color: #94a3b8 !important;
    font-size: 11px !important;
    font-weight: 600 !important;
    letter-spacing: 0.07em !important;
    text-transform: uppercase !important;
}
[data-testid="stSidebar"] .stSelectbox > div > div {
    background: #1e3045 !important;
    border-color: #2d4a6a !important;
    color: #e2e8f0 !important;
}
[data-testid="stSidebar"] .stButton > button {
    background: #2563eb !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 13px !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: #1d4ed8 !important;
}

/* White metric card */
.metric-card {
    background: #ffffff;
    border-radius: 12px;
    padding: 20px 24px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04);
    border: 1px solid #e2e8f0;
}
.metric-value {
    font-size: 36px;
    font-weight: 700;
    line-height: 1;
    letter-spacing: -0.02em;
}
.metric-label {
    font-size: 12px;
    font-weight: 600;
    color: #64748b;
    text-transform: uppercase;
    letter-spacing: 0.07em;
    margin-top: 6px;
}
.metric-sub {
    font-size: 12px;
    color: #94a3b8;
    margin-top: 4px;
}

/* White content card */
.content-card {
    background: #ffffff;
    border-radius: 12px;
    padding: 20px 24px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.06);
    border: 1px solid #e2e8f0;
    margin-bottom: 12px;
}

/* Finding row */
.finding-row {
    background: #ffffff;
    border-radius: 10px;
    padding: 14px 18px;
    margin: 8px 0;
    border: 1px solid #e2e8f0;
    box-shadow: 0 1px 2px rgba(0,0,0,0.04);
}
.finding-row-critical { border-left: 4px solid #dc2626; }
.finding-row-high     { border-left: 4px solid #ea580c; }
.finding-row-medium   { border-left: 4px solid #d97706; }
.finding-row-low      { border-left: 4px solid #64748b; }
.finding-row-ux       { border-left: 4px solid #2563eb; }
.finding-row-suggest  { border-left: 4px solid #059669; }

.finding-title {
    font-size: 14px;
    font-weight: 600;
    color: #111827;
}
.finding-desc {
    font-size: 13px;
    color: #6b7280;
    margin-top: 4px;
    line-height: 1.5;
}

/* Severity pill */
.pill {
    display: inline-block;
    padding: 2px 9px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.04em;
    text-transform: uppercase;
    margin-left: 8px;
    vertical-align: middle;
}
.pill-critical { background: #fee2e2; color: #991b1b; }
.pill-high     { background: #ffedd5; color: #9a3412; }
.pill-medium   { background: #fef3c7; color: #92400e; }
.pill-low      { background: #f1f5f9; color: #475569; }

/* Section heading */
.section-heading {
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.09em;
    text-transform: uppercase;
    color: #94a3b8;
    margin: 20px 0 10px 0;
}

/* Page header */
.page-header {
    background: #ffffff;
    border-radius: 12px;
    padding: 18px 24px;
    border: 1px solid #e2e8f0;
    margin-bottom: 20px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}

/* Agent turn card */
.turn-card {
    background: #ffffff;
    border-radius: 10px;
    border: 1px solid #e2e8f0;
    padding: 16px 20px;
    margin: 8px 0;
    box-shadow: 0 1px 2px rgba(0,0,0,0.04);
}
.turn-label {
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.07em;
    text-transform: uppercase;
    margin-bottom: 6px;
}
.turn-text {
    font-size: 14px;
    color: #374151;
    line-height: 1.6;
}

/* Step status chip */
.chip {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 11px;
    font-weight: 600;
}
.chip-pass    { background: #dcfce7; color: #166534; }
.chip-warning { background: #fef9c3; color: #854d0e; }
.chip-fail    { background: #fee2e2; color: #991b1b; }
.chip-done    { background: #dbeafe; color: #1e40af; }
.chip-stopped { background: #f1f5f9; color: #475569; }

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    background: transparent;
    gap: 0;
    border-bottom: 2px solid #e2e8f0;
}
.stTabs [data-baseweb="tab"] {
    background: transparent;
    border: none;
    color: #64748b;
    font-size: 13px;
    font-weight: 500;
    padding: 10px 20px;
}
.stTabs [aria-selected="true"] {
    color: #2563eb !important;
    border-bottom: 2px solid #2563eb !important;
    font-weight: 600;
}
</style>
""", unsafe_allow_html=True)

# ── Session state ───────────────────────────────────────────────────────────────

if "conversation" not in st.session_state:
    st.session_state.conversation: list[dict] = []
if "run_result" not in st.session_state:
    st.session_state.run_result: QARunResult | None = None
if "running" not in st.session_state:
    st.session_state.running = False
if "latest_run_id" not in st.session_state:
    st.session_state.latest_run_id: str | None = None

# ── Helpers ────────────────────────────────────────────────────────────────────

def get_report_files() -> list[Path]:
    if not REPORTS_DIR.exists():
        return []
    return sorted(REPORTS_DIR.glob("run_*.md"), key=lambda p: p.stat().st_mtime, reverse=True)


def severity_pill(severity: str) -> str:
    s = severity.lower()
    cls = {"critical": "pill-critical", "high": "pill-high", "medium": "pill-medium"}.get(s, "pill-low")
    return f'<span class="pill {cls}">{severity}</span>'


def status_chip(status: str) -> str:
    cls = {
        "PASS": "chip-pass", "WARNING": "chip-warning", "FAIL": "chip-fail",
        "DONE": "chip-done", "STOPPED": "chip-stopped",
    }.get(status, "chip-stopped")
    label = {"PASS": "Pass", "WARNING": "Warning", "FAIL": "Fail", "DONE": "Done", "STOPPED": "Stopped"}.get(status, status)
    return f'<span class="chip {cls}">{label}</span>'


def finding_row(f: ParsedFinding) -> None:
    if f.kind == "bug":
        sev = f.severity.lower()
        row_cls = f"finding-row finding-row-{sev}" if sev in ("critical", "high", "medium") else "finding-row finding-row-low"
        pill = severity_pill(f.severity)
        st.markdown(
            f'<div class="{row_cls}">'
            f'<div class="finding-title">{f.title}{pill}</div>'
            f'<div class="finding-desc">{f.description}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    elif f.kind == "ux_issue":
        pill = severity_pill(f.severity) if f.severity else ""
        st.markdown(
            f'<div class="finding-row finding-row-ux">'
            f'<div class="finding-title">{f.title}{pill}</div>'
            f'<div class="finding-desc">{f.description}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div class="finding-row finding-row-suggest">'
            f'<div class="finding-title">{f.title}</div>'
            f'<div class="finding-desc">{f.description}</div>'
            f'</div>',
            unsafe_allow_html=True,
        )


# ── Sidebar ────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown(
        '<div style="padding: 8px 0 20px 0">'
        '<div style="font-size:20px;font-weight:700;color:#f8fafc;letter-spacing:-0.02em">QA Commander</div>'
        '<div style="font-size:11px;color:#475569;margin-top:3px">Gemini Live · Multimodal Agent</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    st.divider()
    st.markdown("**Target URL**")
    target_url = st.text_input("URL", value="https://example.com", key="target_url", label_visibility="collapsed")

    st.markdown("**Depth**")
    max_steps = st.slider("Steps", min_value=1, max_value=8, value=3, key="max_steps", label_visibility="collapsed")
    st.caption(f"{max_steps} step{'s' if max_steps != 1 else ''}")

    st.divider()
    st.markdown("**Voice Command**")
    try:
        audio_input = st.audio_input("Record", key="voice_cmd", label_visibility="collapsed")
    except Exception:
        audio_input = None
        st.caption("Microphone unavailable — use text below")

    st.markdown("**Text Instruction**")
    text_cmd = st.text_area(
        "Instruction",
        placeholder="e.g. Check all navigation links work",
        key="text_cmd",
        height=72,
        label_visibility="collapsed",
    )

    st.divider()
    run_btn = st.button("Run QA Agent", type="primary", use_container_width=True, disabled=st.session_state.running)
    if st.button("Clear session", use_container_width=True):
        st.session_state.conversation = []
        st.session_state.run_result = None
        st.session_state.latest_run_id = None
        st.rerun()

    st.divider()
    st.markdown("**Run History**")
    report_files = get_report_files()
    if report_files:
        default_idx = 0
        if st.session_state.latest_run_id:
            latest_name = f"run_{st.session_state.latest_run_id}.md"
            names = [r.name for r in report_files]
            if latest_name in names:
                default_idx = names.index(latest_name)
        selected_report_name = st.selectbox(
            "History",
            [r.name for r in report_files],
            index=default_idx,
            key="history_select",
            label_visibility="collapsed",
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

        with st.spinner("Running audit…"):
            result = run_live_agent(
                target_url=target_url,
                max_steps=max_steps,
                user_audio=user_audio,
                user_text=text_cmd.strip() or None,
                on_turn=on_turn_callback,
                headless=True,
            )

        st.session_state.run_result = result
        st.session_state.latest_run_id = result.run_id
        st.session_state.running = False
        st.rerun()

# ── Page header ────────────────────────────────────────────────────────────────

result: QARunResult | None = st.session_state.run_result

st.markdown(
    '<div class="page-header">'
    '<div style="font-size:22px;font-weight:700;color:#0f172a;letter-spacing:-0.02em">QA Commander</div>'
    '<div style="font-size:13px;color:#64748b;margin-top:2px">Multimodal QA & UX audit powered by Gemini Live</div>'
    '</div>',
    unsafe_allow_html=True,
)

# ── Metric cards ────────────────────────────────────────────────────────────────

if result:
    bugs = result.all_bugs
    ux_issues = result.all_ux_issues
    suggestions = result.all_suggestions
    critical = result.critical_count
    summ = result.summary

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        c = "#dc2626" if critical > 0 else "#111827"
        st.markdown(f'<div class="metric-card"><div class="metric-value" style="color:{c}">{critical}</div><div class="metric-label">Critical Bugs</div><div class="metric-sub">Severity: Critical</div></div>', unsafe_allow_html=True)

    with col2:
        c = "#ea580c" if len(bugs) > 0 else "#111827"
        st.markdown(f'<div class="metric-card"><div class="metric-value" style="color:{c}">{len(bugs)}</div><div class="metric-label">Total Bugs</div><div class="metric-sub">All severities</div></div>', unsafe_allow_html=True)

    with col3:
        c = "#2563eb" if len(ux_issues) > 0 else "#111827"
        st.markdown(f'<div class="metric-card"><div class="metric-value" style="color:{c}">{len(ux_issues)}</div><div class="metric-label">UX Issues</div><div class="metric-sub">Design & usability</div></div>', unsafe_allow_html=True)

    with col4:
        c = "#059669" if len(suggestions) > 0 else "#111827"
        st.markdown(f'<div class="metric-card"><div class="metric-value" style="color:{c}">{len(suggestions)}</div><div class="metric-label">Suggestions</div><div class="metric-sub">Actionable improvements</div></div>', unsafe_allow_html=True)

    with col5:
        pass_pct = int(summ["pass"] / summ["total"] * 100) if summ["total"] > 0 else 0
        c = "#059669" if pass_pct >= 80 else "#d97706" if pass_pct >= 50 else "#dc2626"
        st.markdown(f'<div class="metric-card"><div class="metric-value" style="color:{c}">{pass_pct}%</div><div class="metric-label">Steps Passed</div><div class="metric-sub">{summ["pass"]} of {summ["total"]} steps</div></div>', unsafe_allow_html=True)

    st.markdown("<div style='margin-top:8px'></div>", unsafe_allow_html=True)

else:
    st.markdown(
        '<div style="background:#ffffff;border-radius:12px;padding:32px;text-align:center;'
        'border:1px dashed #e2e8f0;margin-bottom:16px">'
        '<div style="font-size:28px;margin-bottom:12px">⬡</div>'
        '<div style="font-size:15px;font-weight:600;color:#374151">Ready to audit</div>'
        '<div style="font-size:13px;color:#9ca3af;margin-top:6px">Enter a URL in the sidebar and click Run QA Agent</div>'
        '</div>',
        unsafe_allow_html=True,
    )

# ── Tabs ───────────────────────────────────────────────────────────────────────

tab_findings, tab_feed, tab_steps, tab_report, tab_screenshots = st.tabs(
    ["Findings", "Live Feed", "Step Details", "Report", "Screenshots"]
)

# ── Tab 1: Findings ─────────────────────────────────────────────────────────────

with tab_findings:
    if result is None:
        st.markdown('<div style="color:#9ca3af;font-size:14px;padding:20px 0">No findings yet — run the agent first.</div>', unsafe_allow_html=True)
    else:
        bugs = result.all_bugs
        ux_issues = result.all_ux_issues
        suggestions = result.all_suggestions
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}

        if bugs:
            st.markdown('<div class="section-heading">Bugs</div>', unsafe_allow_html=True)
            for f in sorted(bugs, key=lambda x: severity_order.get(x.severity.lower(), 9)):
                finding_row(f)

        if ux_issues:
            st.markdown('<div class="section-heading">UX & Design Issues</div>', unsafe_allow_html=True)
            for f in ux_issues:
                finding_row(f)

        if suggestions:
            st.markdown('<div class="section-heading">Suggestions</div>', unsafe_allow_html=True)
            for f in suggestions:
                finding_row(f)

        if not bugs and not ux_issues and not suggestions:
            st.markdown('<div style="color:#9ca3af;font-size:14px;padding:20px 0">No structured findings — check Live Feed for agent narration.</div>', unsafe_allow_html=True)

# ── Tab 2: Live Feed ────────────────────────────────────────────────────────────

with tab_feed:
    if not st.session_state.conversation:
        st.markdown('<div style="color:#9ca3af;font-size:14px;padding:20px 0">Run the agent to see the live feed.</div>', unsafe_allow_html=True)
    else:
        for msg in st.session_state.conversation:
            if msg["role"] == "user":
                st.markdown(
                    f'<div class="turn-card" style="border-left:4px solid #059669">'
                    f'<div class="turn-label" style="color:#059669">Tester</div>'
                    f'<div class="turn-text">{msg["content"]}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                if msg.get("audio"):
                    st.audio(msg["audio"], format="audio/wav")
            else:
                step = msg.get("step", "")
                chip = status_chip(msg.get("status", ""))
                narration = msg.get("content", "")
                st.markdown(
                    f'<div class="turn-card" style="border-left:4px solid #2563eb">'
                    f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:8px">'
                    f'<span class="turn-label" style="color:#2563eb">Step {step}</span>{chip}'
                    f'</div>'
                    f'<div class="turn-text">{narration}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                if msg.get("audio"):
                    st.audio(msg["audio"], format="audio/wav")
                step_findings: list[ParsedFinding] = msg.get("findings", [])
                if step_findings:
                    with st.expander(f"{len(step_findings)} finding(s) from this step"):
                        for f in step_findings:
                            finding_row(f)

# ── Tab 3: Step Details ─────────────────────────────────────────────────────────

with tab_steps:
    if result is None:
        st.markdown('<div style="color:#9ca3af;font-size:14px;padding:20px 0">No run data yet.</div>', unsafe_allow_html=True)
    else:
        for step in result.steps:
            icon = {"PASS": "✅", "WARNING": "⚠️", "FAIL": "❌", "DONE": "🏁", "STOPPED": "🛑"}.get(step.status, "❓")
            with st.expander(f"{icon} Step {step.step} — {step.status} — clicked: {step.click_target or 'none'}"):
                col_a, col_b = st.columns(2)
                col_a.markdown(f"**Before URL**\n\n{step.before_url}")
                col_b.markdown(f"**After URL**\n\n{step.after_url}")
                if step.agent_narration:
                    st.markdown(
                        f'<div class="content-card"><div class="turn-text">{step.agent_narration}</div></div>',
                        unsafe_allow_html=True,
                    )
                cols = st.columns(3)
                cols[0].metric("Console errors", len(step.console_errors))
                cols[1].metric("Network failures", len(step.network_failures))
                cols[2].metric("Findings", len(step.findings))
                if step.visual_flags:
                    for flag in step.visual_flags:
                        st.warning(flag)
                if step.error:
                    st.error(step.error)
                if step.findings:
                    st.markdown("**Findings this step**")
                    for f in step.findings:
                        finding_row(f)

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
        st.markdown(f'<div class="content-card">{report_text}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div style="color:#9ca3af;font-size:14px;padding:20px 0">No report available yet.</div>', unsafe_allow_html=True)

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
        st.markdown('<div style="color:#9ca3af;font-size:14px;padding:20px 0">Screenshots appear here after a run.</div>', unsafe_allow_html=True)
