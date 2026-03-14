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

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* Hide Streamlit default chrome */
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    header { visibility: hidden; }

    /* Main background */
    .stApp {
        background-color: #09090b;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #0f0f11;
        border-right: 1px solid #1e1e23;
    }

    /* Finding cards */
    .finding-bug-critical {
        background: #1a0a0a;
        border-left: 3px solid #ef4444;
        border-radius: 6px;
        padding: 12px 16px;
        margin: 6px 0;
    }
    .finding-bug-high {
        background: #160e07;
        border-left: 3px solid #f97316;
        border-radius: 6px;
        padding: 12px 16px;
        margin: 6px 0;
    }
    .finding-bug-medium {
        background: #14110a;
        border-left: 3px solid #f59e0b;
        border-radius: 6px;
        padding: 12px 16px;
        margin: 6px 0;
    }
    .finding-bug-low {
        background: #0d1117;
        border-left: 3px solid #6b7280;
        border-radius: 6px;
        padding: 12px 16px;
        margin: 6px 0;
    }
    .finding-ux {
        background: #0a0f1a;
        border-left: 3px solid #3b82f6;
        border-radius: 6px;
        padding: 12px 16px;
        margin: 6px 0;
    }
    .finding-suggestion {
        background: #090f0e;
        border-left: 3px solid #10b981;
        border-radius: 6px;
        padding: 12px 16px;
        margin: 6px 0;
    }

    /* Severity badges */
    .badge {
        display: inline-block;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 11px;
        font-weight: 600;
        letter-spacing: 0.05em;
        text-transform: uppercase;
    }
    .badge-critical { background: #7f1d1d; color: #fca5a5; }
    .badge-high     { background: #7c2d12; color: #fdba74; }
    .badge-medium   { background: #78350f; color: #fcd34d; }
    .badge-low      { background: #1f2937; color: #9ca3af; }

    /* Status badges */
    .status-pass    { color: #22c55e; font-weight: 600; }
    .status-warn    { color: #f59e0b; font-weight: 600; }
    .status-fail    { color: #ef4444; font-weight: 600; }
    .status-done    { color: #3b82f6; font-weight: 600; }
    .status-stopped { color: #6b7280; font-weight: 600; }

    /* Agent message */
    .agent-turn {
        background: #111115;
        border: 1px solid #1e1e26;
        border-radius: 8px;
        padding: 14px 18px;
        margin: 8px 0;
    }

    /* Metric number */
    .metric-num {
        font-size: 32px;
        font-weight: 700;
        line-height: 1;
    }
    .metric-label {
        font-size: 12px;
        color: #71717a;
        margin-top: 4px;
        text-transform: uppercase;
        letter-spacing: 0.06em;
    }

    /* Section label */
    .section-label {
        font-size: 11px;
        font-weight: 600;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: #52525b;
        margin: 20px 0 8px 0;
    }

    /* Override Streamlit tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        background: transparent;
        border-bottom: 1px solid #1e1e23;
    }
    .stTabs [data-baseweb="tab"] {
        background: transparent;
        border: none;
        color: #71717a;
        font-size: 13px;
        font-weight: 500;
        padding: 8px 16px;
    }
    .stTabs [aria-selected="true"] {
        background: transparent;
        color: #fafafa;
        border-bottom: 2px solid #3b82f6;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

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


def severity_badge(severity: str) -> str:
    sev = severity.lower()
    cls = {"critical": "badge-critical", "high": "badge-high", "medium": "badge-medium", "low": "badge-low"}.get(
        sev, "badge-low"
    )
    return f'<span class="badge {cls}">{severity}</span>'


def finding_card(f: ParsedFinding) -> None:
    if f.kind == "bug":
        sev = f.severity.lower()
        cls = f"finding-bug-{sev}" if sev in ("critical", "high", "medium", "low") else "finding-bug-medium"
        badge = severity_badge(f.severity)
        st.markdown(
            f'<div class="{cls}"><strong>{f.title}</strong> {badge}'
            f'<div style="color:#a1a1aa;font-size:13px;margin-top:4px">{f.description}</div></div>',
            unsafe_allow_html=True,
        )
    elif f.kind == "ux_issue":
        badge = severity_badge(f.severity) if f.severity else ""
        st.markdown(
            f'<div class="finding-ux"><strong>{f.title}</strong> {badge}'
            f'<div style="color:#a1a1aa;font-size:13px;margin-top:4px">{f.description}</div></div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div class="finding-suggestion"><strong>{f.title}</strong>'
            f'<div style="color:#a1a1aa;font-size:13px;margin-top:4px">{f.description}</div></div>',
            unsafe_allow_html=True,
        )


# ── Sidebar ────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown(
        '<div style="padding:4px 0 16px 0">'
        '<span style="font-size:18px;font-weight:700;letter-spacing:-0.02em;color:#fafafa">QA Commander</span>'
        '<span style="font-size:11px;color:#52525b;display:block;margin-top:2px">Powered by Gemini Live API</span>'
        "</div>",
        unsafe_allow_html=True,
    )

    st.divider()

    st.markdown('<div class="section-label">Target</div>', unsafe_allow_html=True)
    target_url = st.text_input("URL", value="https://example.com", key="target_url", label_visibility="collapsed")

    st.markdown('<div class="section-label">Depth</div>', unsafe_allow_html=True)
    max_steps = st.slider("Steps", min_value=1, max_value=8, value=3, key="max_steps", label_visibility="collapsed")
    st.caption(f"{max_steps} interaction step{'s' if max_steps != 1 else ''}")

    st.divider()

    st.markdown('<div class="section-label">Voice Command</div>', unsafe_allow_html=True)
    try:
        audio_input = st.audio_input("Record instruction", key="voice_cmd", label_visibility="collapsed")
    except Exception:
        audio_input = None
        st.caption("Microphone unavailable — use text below")

    st.markdown('<div class="section-label">Text Instruction</div>', unsafe_allow_html=True)
    text_cmd = st.text_area(
        "Instruction",
        placeholder="e.g. Check all navigation links work",
        key="text_cmd",
        height=72,
        label_visibility="collapsed",
    )

    st.divider()

    run_btn = st.button(
        "Run Agent",
        type="primary",
        use_container_width=True,
        disabled=st.session_state.running,
    )

    if st.button("Clear", use_container_width=True):
        st.session_state.conversation = []
        st.session_state.run_result = None
        st.session_state.latest_run_id = None
        st.rerun()

    st.divider()

    st.markdown('<div class="section-label">Run History</div>', unsafe_allow_html=True)
    report_files = get_report_files()
    if report_files:
        # Auto-select latest run if we just completed one
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
                user_audio = audio_input.read()
                if not user_audio:
                    user_audio = None
            except Exception:
                user_audio = None

        if user_audio:
            st.session_state.conversation.append(
                {"role": "user", "content": "Voice command recorded", "audio": user_audio}
            )
        elif text_cmd.strip():
            st.session_state.conversation.append(
                {"role": "user", "content": text_cmd.strip()}
            )

        st.session_state.running = True

        def on_turn_callback(step: int, record: StepRecord) -> None:
            st.session_state.conversation.append(
                {
                    "role": "agent",
                    "step": step,
                    "content": record.agent_narration,
                    "status": record.status,
                    "audio": record.audio_wav,
                    "screenshot": record.screenshot,
                    "findings": record.findings,
                }
            )

        with st.spinner("Running QA audit…"):
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

# ── Main header ────────────────────────────────────────────────────────────────

result: QARunResult | None = st.session_state.run_result

st.markdown(
    '<h1 style="font-size:26px;font-weight:700;letter-spacing:-0.03em;margin:0 0 4px 0;color:#fafafa">'
    "QA Commander</h1>",
    unsafe_allow_html=True,
)

if result:
    summ = result.summary
    bugs = result.all_bugs
    ux = result.all_ux_issues
    suggestions = result.all_suggestions
    critical = result.critical_count

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        color = "#ef4444" if critical > 0 else "#fafafa"
        st.markdown(
            f'<div style="padding:16px 0"><div class="metric-num" style="color:{color}">{critical}</div>'
            f'<div class="metric-label">Critical Bugs</div></div>',
            unsafe_allow_html=True,
        )
    with col2:
        color = "#f97316" if len(bugs) > 0 else "#fafafa"
        st.markdown(
            f'<div style="padding:16px 0"><div class="metric-num" style="color:{color}">{len(bugs)}</div>'
            f'<div class="metric-label">Total Bugs</div></div>',
            unsafe_allow_html=True,
        )
    with col3:
        st.markdown(
            f'<div style="padding:16px 0"><div class="metric-num" style="color:#3b82f6">{len(ux)}</div>'
            f'<div class="metric-label">UX Issues</div></div>',
            unsafe_allow_html=True,
        )
    with col4:
        st.markdown(
            f'<div style="padding:16px 0"><div class="metric-num" style="color:#10b981">{len(suggestions)}</div>'
            f'<div class="metric-label">Suggestions</div></div>',
            unsafe_allow_html=True,
        )
    st.divider()
else:
    st.markdown(
        '<p style="color:#52525b;font-size:14px;margin:4px 0 20px 0">'
        "Enter a URL and run the agent to begin your audit.</p>",
        unsafe_allow_html=True,
    )

# ── Tabs ───────────────────────────────────────────────────────────────────────

tab_findings, tab_feed, tab_report, tab_screenshots = st.tabs(
    ["Findings", "Live Feed", "Report", "Screenshots"]
)

# ── Tab 1: Findings ────────────────────────────────────────────────────────────

with tab_findings:
    if result is None:
        st.markdown('<p style="color:#52525b;font-size:14px">No findings yet.</p>', unsafe_allow_html=True)
    else:
        bugs = result.all_bugs
        ux_issues = result.all_ux_issues
        suggestions = result.all_suggestions

        if bugs:
            st.markdown('<div class="section-label">Bugs</div>', unsafe_allow_html=True)
            # Sort bugs: critical first
            severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
            for f in sorted(bugs, key=lambda x: severity_order.get(x.severity.lower(), 9)):
                finding_card(f)

        if ux_issues:
            st.markdown('<div class="section-label">UX & Design Issues</div>', unsafe_allow_html=True)
            for f in ux_issues:
                finding_card(f)

        if suggestions:
            st.markdown('<div class="section-label">Suggestions</div>', unsafe_allow_html=True)
            for f in suggestions:
                finding_card(f)

        if not bugs and not ux_issues and not suggestions:
            st.markdown(
                '<p style="color:#52525b;font-size:14px">No structured findings were parsed. '
                "Check the Live Feed tab for agent narration.</p>",
                unsafe_allow_html=True,
            )

# ── Tab 2: Live Feed ───────────────────────────────────────────────────────────

with tab_feed:
    if not st.session_state.conversation:
        st.markdown('<p style="color:#52525b;font-size:14px">Run the agent to see the live feed.</p>', unsafe_allow_html=True)
    else:
        for msg in st.session_state.conversation:
            if msg["role"] == "user":
                st.markdown(
                    f'<div class="agent-turn" style="border-color:#1e2d1e">'
                    f'<span style="font-size:11px;font-weight:600;color:#4ade80;letter-spacing:0.06em;text-transform:uppercase">Tester</span>'
                    f'<div style="margin-top:6px;color:#d4d4d8">{msg["content"]}</div></div>',
                    unsafe_allow_html=True,
                )
                if msg.get("audio"):
                    st.audio(msg["audio"], format="audio/wav")
            else:
                step = msg.get("step", "")
                status = msg.get("status", "")
                status_color = {
                    "PASS": "#22c55e", "WARNING": "#f59e0b", "FAIL": "#ef4444",
                    "DONE": "#3b82f6", "STOPPED": "#6b7280"
                }.get(status, "#6b7280")
                narration = msg.get("content", "")
                st.markdown(
                    f'<div class="agent-turn">'
                    f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:6px">'
                    f'<span style="font-size:11px;font-weight:600;color:#71717a;letter-spacing:0.06em;text-transform:uppercase">Step {step}</span>'
                    f'<span style="font-size:11px;font-weight:600;color:{status_color}">{status}</span>'
                    f"</div>"
                    f'<div style="color:#d4d4d8;line-height:1.6">{narration}</div></div>',
                    unsafe_allow_html=True,
                )
                if msg.get("audio"):
                    st.audio(msg["audio"], format="audio/wav")
                # Show step findings inline
                step_findings: list[ParsedFinding] = msg.get("findings", [])
                if step_findings:
                    with st.expander(f"{len(step_findings)} finding(s) this step"):
                        for f in step_findings:
                            finding_card(f)

# ── Tab 3: Report ──────────────────────────────────────────────────────────────

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
        st.download_button(
            "Download report",
            data=report_text,
            file_name=report_to_show.name,
            mime="text/markdown",
        )
        st.markdown(report_text)
    else:
        st.markdown('<p style="color:#52525b;font-size:14px">No report available.</p>', unsafe_allow_html=True)

# ── Tab 4: Screenshots ─────────────────────────────────────────────────────────

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
                st.image(str(shot), caption=shot.stem.replace("_", " ").title(), use_container_width=True)
    else:
        st.markdown('<p style="color:#52525b;font-size:14px">Screenshots appear here after a run.</p>', unsafe_allow_html=True)
