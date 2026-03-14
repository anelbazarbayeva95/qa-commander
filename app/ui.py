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
    "Check all navigation links and CTAs",
    "Audit accessibility: contrast, labels, focus",
    "Identify bad design patterns and layout issues",
    "Test the signup or checkout flow",
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
@import url('https://fonts.googleapis.com/css2?family=Inter:ital,wght@0,300;0,400;0,500;0,600;0,700;1,400&display=swap');

*, *::before, *::after {
    font-family: 'Inter', system-ui, -apple-system, sans-serif !important;
    box-sizing: border-box;
}
#MainMenu, footer, header { visibility: hidden; }

/* ── Full light background ── */
.stApp                          { background: #f8fafc; }
[data-testid="stSidebar"]       { background: #ffffff !important; border-right: 1px solid #e2e8f0 !important; }
[data-testid="stSidebar"] *     { color: #374151 !important; }
[data-testid="stSidebar"] label { color: #6b7280 !important; font-size: 12px !important; font-weight: 600 !important; }
[data-testid="stSidebar"] hr    { border-color: #f1f5f9 !important; }

/* Sidebar inputs */
[data-testid="stSidebar"] input,
[data-testid="stSidebar"] textarea {
    background: #f8fafc !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 8px !important;
    color: #111827 !important;
    font-size: 13px !important;
}
[data-testid="stSidebar"] input:focus,
[data-testid="stSidebar"] textarea:focus {
    border-color: #2563eb !important;
    box-shadow: 0 0 0 3px rgba(37,99,235,.08) !important;
}
[data-testid="stSidebar"] .stSelectbox > div > div {
    background: #f8fafc !important; border-color: #e2e8f0 !important; color: #111827 !important;
}

/* Primary button */
[data-testid="stSidebar"] .stButton button[kind="primary"],
[data-testid="stSidebar"] .stButton button[data-testid="baseButton-primary"] {
    background: #2563eb !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 13px !important;
    padding: 10px 0 !important;
    box-shadow: 0 1px 3px rgba(37,99,235,.3) !important;
}
[data-testid="stSidebar"] .stButton button[kind="primary"]:hover {
    background: #1d4ed8 !important;
}
/* Secondary button */
[data-testid="stSidebar"] .stButton button[kind="secondary"],
[data-testid="stSidebar"] .stButton button[data-testid="baseButton-secondary"] {
    background: #f1f5f9 !important;
    color: #374151 !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 8px !important;
    font-weight: 500 !important;
    font-size: 13px !important;
}

/* ── Cards ── */
.card {
    background: #fff; border-radius: 12px; padding: 20px 24px;
    border: 1px solid #e2e8f0; box-shadow: 0 1px 3px rgba(0,0,0,.04);
    margin-bottom: 12px;
}

/* ── Metric card ── */
.m-card {
    background: #fff; border-radius: 12px; padding: 20px 22px;
    border: 1px solid #e2e8f0; box-shadow: 0 1px 3px rgba(0,0,0,.04);
}
.m-val  { font-size: 34px; font-weight: 700; line-height: 1; letter-spacing: -.025em; }
.m-lbl  { font-size: 11px; font-weight: 600; color: #64748b; text-transform: uppercase; letter-spacing: .07em; margin-top: 5px; }
.m-sub  { font-size: 12px; color: #9ca3af; margin-top: 3px; }

/* ── Step timeline dots ── */
.timeline { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; margin: 14px 0 18px; }
.t-dot {
    width: 30px; height: 30px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 12px; font-weight: 700; flex-shrink: 0;
}
.t-pass    { background: #dcfce7; color: #166534; }
.t-warning { background: #fef9c3; color: #854d0e; }
.t-fail    { background: #fee2e2; color: #991b1b; }
.t-done    { background: #dbeafe; color: #1e40af; }
.t-stopped { background: #f1f5f9; color: #64748b; }
.t-line    { height: 2px; flex: 1; min-width: 12px; background: #e2e8f0; }

/* ── Finding rows ── */
.f-row {
    background: #fff; border-radius: 10px; padding: 13px 16px;
    margin: 7px 0; border: 1px solid #e2e8f0;
    box-shadow: 0 1px 2px rgba(0,0,0,.03);
}
.f-critical { border-left: 4px solid #dc2626; }
.f-high     { border-left: 4px solid #ea580c; }
.f-medium   { border-left: 4px solid #d97706; }
.f-low      { border-left: 4px solid #94a3b8; }
.f-ux       { border-left: 4px solid #2563eb; }
.f-suggest  { border-left: 4px solid #059669; }
.f-dim      { opacity: .4; }
.f-title    { font-size: 14px; font-weight: 600; color: #111827; }
.f-desc     { font-size: 13px; color: #6b7280; margin-top: 4px; line-height: 1.55; }

/* ── Pills ── */
.pill {
    display: inline-block; padding: 2px 8px; border-radius: 20px;
    font-size: 11px; font-weight: 600; text-transform: uppercase;
    letter-spacing: .04em; margin-left: 7px; vertical-align: middle;
}
.p-critical  { background: #fee2e2; color: #991b1b; }
.p-high      { background: #ffedd5; color: #9a3412; }
.p-medium    { background: #fef3c7; color: #92400e; }
.p-low       { background: #f1f5f9; color: #475569; }
.p-confirmed { background: #dcfce7; color: #166534; }
.p-dismissed { background: #f1f5f9; color: #94a3b8; }

/* ── Status chips ── */
.chip { display: inline-block; padding: 3px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; }
.c-pass    { background: #dcfce7; color: #166534; }
.c-warning { background: #fef9c3; color: #854d0e; }
.c-fail    { background: #fee2e2; color: #991b1b; }
.c-done    { background: #dbeafe; color: #1e40af; }
.c-stopped { background: #f1f5f9; color: #64748b; }

/* ── Conversation turns ── */
.turn {
    background: #fff; border-radius: 10px; border: 1px solid #e2e8f0;
    padding: 14px 18px; margin: 7px 0; box-shadow: 0 1px 2px rgba(0,0,0,.03);
}

/* ── Section heading ── */
.sh {
    font-size: 11px; font-weight: 700; letter-spacing: .09em;
    text-transform: uppercase; color: #9ca3af; margin: 18px 0 8px;
}

/* ── Prompt chips ── */
.pc {
    display: inline-block; background: #fff; border: 1px solid #e2e8f0;
    border-radius: 20px; padding: 6px 14px; font-size: 13px; color: #374151;
    margin: 4px; box-shadow: 0 1px 2px rgba(0,0,0,.04);
}

/* ── Tabs ── */
.stTabs [data-baseweb="tab-list"] { background: transparent; gap: 0; border-bottom: 2px solid #e2e8f0; }
.stTabs [data-baseweb="tab"]      { background: transparent; border: none; color: #64748b; font-size: 13px; font-weight: 500; padding: 10px 20px; }
.stTabs [aria-selected="true"]    { color: #2563eb !important; border-bottom: 2px solid #2563eb !important; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

# ── Session state ───────────────────────────────────────────────────────────────

for k, v in {
    "conversation": [],
    "run_result": None,
    "running": False,
    "latest_run_id": None,
    "agent_log": [],
    "dismissed": set(),
    "confirmed": set(),
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── Helpers ────────────────────────────────────────────────────────────────────

def get_report_files() -> list[Path]:
    if not REPORTS_DIR.exists():
        return []
    return sorted(REPORTS_DIR.glob("run_*.md"), key=lambda p: p.stat().st_mtime, reverse=True)


def clean_url(raw: str) -> str:
    """Strip whitespace and fix duplicate scheme."""
    url = raw.strip()
    # Remove double https:// or http://
    for scheme in ("https://https://", "http://http://", "https://http://", "http://https://"):
        if url.startswith(scheme):
            url = "https://" + url[len(scheme):]
    return url


def fkey(f: ParsedFinding) -> str:
    return f"{f.kind}:{f.title}"


def sev_pill(sev: str) -> str:
    s = sev.lower()
    c = {"critical": "p-critical", "high": "p-high", "medium": "p-medium"}.get(s, "p-low")
    return f'<span class="pill {c}">{sev}</span>'


def step_chip(status: str) -> str:
    c = {"PASS": "c-pass", "WARNING": "c-warning", "FAIL": "c-fail", "DONE": "c-done", "STOPPED": "c-stopped"}.get(status, "c-stopped")
    l = {"PASS": "Pass", "WARNING": "Warning", "FAIL": "Fail", "DONE": "Done", "STOPPED": "Stopped"}.get(status, status)
    return f'<span class="chip {c}">{l}</span>'


def finding_html(f: ParsedFinding, extra: str = "") -> str:
    if f.kind == "bug":
        sev = f.severity.lower()
        row = f"f-row f-{sev}" if sev in ("critical", "high", "medium") else "f-row f-low"
        pill = sev_pill(f.severity)
    elif f.kind == "ux_issue":
        row, pill = "f-row f-ux", sev_pill(f.severity) if f.severity else ""
    else:
        row, pill = "f-row f-suggest", ""
    if extra:
        row += f" {extra}"
    return (
        f'<div class="{row}">'
        f'<div class="f-title">{f.title}{pill}</div>'
        f'<div class="f-desc">{f.description}</div>'
        f'</div>'
    )


def render_finding(f: ParsedFinding) -> None:
    key = fkey(f)
    dismissed = key in st.session_state.dismissed
    confirmed  = key in st.session_state.confirmed
    st.markdown(finding_html(f, "f-dim" if dismissed else ""), unsafe_allow_html=True)
    ca, cb, _ = st.columns([1, 1, 7])
    if confirmed:
        ca.markdown('<span class="pill p-confirmed">✓ Confirmed</span>', unsafe_allow_html=True)
    else:
        if ca.button("✓", key=f"con_{key}", help="Confirm as real issue"):
            st.session_state.confirmed.add(key)
            st.session_state.dismissed.discard(key)
            st.rerun()
    if dismissed:
        cb.markdown('<span class="pill p-dismissed">Dismissed</span>', unsafe_allow_html=True)
    else:
        if cb.button("✕", key=f"dis_{key}", help="Dismiss"):
            st.session_state.dismissed.add(key)
            st.session_state.confirmed.discard(key)
            st.rerun()


# ── Sidebar ────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown(
        '<div style="padding:12px 0 20px">'
        '<div style="font-size:18px;font-weight:700;color:#0f172a;letter-spacing:-.02em">QA Commander</div>'
        '<div style="font-size:11px;color:#94a3b8;margin-top:2px;font-weight:500">Gemini Live · Multimodal Agent</div>'
        '</div>',
        unsafe_allow_html=True,
    )
    st.divider()

    st.markdown("**Target URL**")
    raw_url = st.text_input("URL", value="https://example.com", key="target_url", label_visibility="collapsed")
    target_url = clean_url(raw_url)
    if target_url != raw_url:
        st.caption(f"→ {target_url}")

    st.markdown("**Audit depth**")
    max_steps = st.slider("Steps", 1, 8, 3, key="max_steps", label_visibility="collapsed")
    st.caption(f"{max_steps} step{'s' if max_steps != 1 else ''}")

    st.divider()

    # Voice input — graceful fallback
    st.markdown("**Voice command** *(optional)*")
    audio_input = None
    try:
        audio_input = st.audio_input("Record instruction", key="voice_cmd", label_visibility="collapsed")
    except Exception:
        st.caption("Voice input unavailable in this browser. Use text below.")

    st.markdown("**Text instruction** *(optional)*")
    text_cmd = st.text_area(
        "Instruction", placeholder="e.g. Check all navigation links work and audit accessibility",
        key="text_cmd", height=80, label_visibility="collapsed",
    )

    st.divider()
    run_btn = st.button("Run QA Agent", type="primary", use_container_width=True, disabled=st.session_state.running)
    if st.button("Clear", use_container_width=True):
        for k in ("conversation", "agent_log"):
            st.session_state[k] = []
        st.session_state.dismissed = set()
        st.session_state.confirmed = set()
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
        st.caption("No previous runs.")
        selected_report_name = None

# ── Run trigger ────────────────────────────────────────────────────────────────

if run_btn and not st.session_state.running:
    if not os.environ.get("GEMINI_API_KEY"):
        st.error("⚠️ Set the GEMINI_API_KEY environment variable before running.")
    else:
        user_audio: bytes | None = None
        if audio_input is not None:
            try:
                data = audio_input.read()
                user_audio = data if data else None
            except Exception:
                user_audio = None

        if user_audio:
            st.session_state.conversation.append({"role": "user", "content": "🎙 Voice command recorded", "audio": user_audio})
        elif text_cmd.strip():
            st.session_state.conversation.append({"role": "user", "content": text_cmd.strip()})

        st.session_state.running = True
        st.session_state.agent_log = []
        st.session_state.dismissed = set()
        st.session_state.confirmed = set()

        def on_turn_callback(step: int, record: StepRecord) -> None:
            st.session_state.agent_log.append(
                f"Step {step} complete — {record.status} — "
                f"clicked: '{record.click_target}'" if record.click_target else f"Step {step} — {record.status}"
            )
            st.session_state.conversation.append({
                "role": "agent", "step": step,
                "content": record.agent_narration,
                "status": record.status,
                "audio": record.audio_wav,
                "screenshot": record.screenshot,
                "findings": record.findings,
            })

        with st.status("Agent is auditing…", expanded=True) as status_box:
            st.write(f"Opening `{target_url}`")
            result = run_live_agent(
                target_url=target_url,
                max_steps=max_steps,
                user_audio=user_audio,
                user_text=text_cmd.strip() or None,
                on_turn=on_turn_callback,
                headless=True,
            )
            for line in st.session_state.agent_log:
                st.write(line)
            if result.success:
                status_box.update(label="✓ Audit complete", state="complete", expanded=False)
            else:
                status_box.update(label=f"✗ {result.error_message}", state="error", expanded=True)

        st.session_state.run_result = result
        st.session_state.latest_run_id = result.run_id
        st.session_state.running = False
        st.rerun()

# ── Header ─────────────────────────────────────────────────────────────────────

result: QARunResult | None = st.session_state.run_result

run_label = ""
if result:
    run_label = (
        f'<span style="font-size:12px;color:#94a3b8;font-weight:500;margin-left:12px">'
        f'Run {result.run_id} · {result.start_url}</span>'
    )

st.markdown(
    f'<div class="card" style="padding:16px 24px;margin-bottom:18px">'
    f'<div style="font-size:20px;font-weight:700;color:#0f172a;letter-spacing:-.02em">'
    f'QA Commander{run_label}</div>'
    f'<div style="font-size:13px;color:#64748b;margin-top:3px">'
    f'Autonomous QA &amp; UX audit · Gemini Live multimodal agent</div>'
    f'</div>',
    unsafe_allow_html=True,
)

# ── Metrics + timeline ─────────────────────────────────────────────────────────

if result:
    bugs       = result.all_bugs
    ux_issues  = result.all_ux_issues
    suggestions = result.all_suggestions
    critical   = result.critical_count
    summ       = result.summary
    pass_pct   = int(summ["pass"] / summ["total"] * 100) if summ["total"] > 0 else 0

    c1, c2, c3, c4, c5 = st.columns(5)
    for col, val, color, label, sub in [
        (c1, critical,         "#dc2626" if critical   > 0 else "#0f172a", "Critical Bugs",  "Severity: Critical"),
        (c2, len(bugs),        "#ea580c" if len(bugs)  > 0 else "#0f172a", "Bugs",           "All severities"),
        (c3, len(ux_issues),   "#2563eb" if ux_issues  else "#0f172a",     "UX Issues",      "Design & usability"),
        (c4, len(suggestions), "#059669" if suggestions else "#0f172a",    "Suggestions",    "Actionable improvements"),
        (c5, f"{pass_pct}%",
             "#059669" if pass_pct >= 80 else "#d97706" if pass_pct >= 50 else "#dc2626",
             "Steps Passed", f"{summ['pass']} of {summ['total']} steps"),
    ]:
        with col:
            st.markdown(
                f'<div class="m-card">'
                f'<div class="m-val" style="color:{color}">{val}</div>'
                f'<div class="m-lbl">{label}</div>'
                f'<div class="m-sub">{sub}</div>'
                f'</div>',
                unsafe_allow_html=True,
            )

    # Timeline
    dot_map = {"PASS": "t-pass", "WARNING": "t-warning", "FAIL": "t-fail", "DONE": "t-done", "STOPPED": "t-stopped"}
    html = '<div class="timeline">'
    for i, s in enumerate(result.steps):
        html += f'<div class="t-dot {dot_map.get(s.status, "t-stopped")}" title="Step {s.step}: {s.status}">{s.step}</div>'
        if i < len(result.steps) - 1:
            html += '<div class="t-line"></div>'
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)

else:
    # Ready state
    st.markdown(
        '<div class="card" style="text-align:center;padding:36px 24px;border-style:dashed">'
        '<div style="font-size:14px;font-weight:600;color:#374151;margin-bottom:6px">Ready to audit</div>'
        '<div style="font-size:13px;color:#94a3b8;margin-bottom:20px">'
        'Enter a URL in the sidebar and click <strong>Run QA Agent</strong></div>'
        '<div class="sh" style="margin:0 0 10px">Suggested focus areas</div>'
        + "".join(f'<span class="pc">{p}</span>' for p in SUGGESTED_PROMPTS)
        + "</div>",
        unsafe_allow_html=True,
    )

# ── Tabs ───────────────────────────────────────────────────────────────────────

tab_findings, tab_feed, tab_steps, tab_report, tab_shots = st.tabs(
    ["Findings", "Live Feed", "Step Details", "Report", "Screenshots"]
)

# ── Findings ───────────────────────────────────────────────────────────────────

with tab_findings:
    if result is None:
        st.markdown('<p style="color:#9ca3af;font-size:14px;padding:16px 0">No findings yet.</p>', unsafe_allow_html=True)
    else:
        bugs       = result.all_bugs
        ux_issues  = result.all_ux_issues
        suggestions = result.all_suggestions
        total      = len(bugs) + len(ux_issues) + len(suggestions)
        n_conf     = sum(1 for f in result.all_findings if fkey(f) in st.session_state.confirmed)
        n_dis      = sum(1 for f in result.all_findings if fkey(f) in st.session_state.dismissed)
        sev_order  = {"critical": 0, "high": 1, "medium": 2, "low": 3}

        if total:
            st.markdown(
                f'<div style="font-size:13px;color:#64748b;margin-bottom:12px">'
                f'{total} finding{"s" if total != 1 else ""} &nbsp;·&nbsp; '
                f'<span style="color:#166534;font-weight:600">{n_conf} confirmed</span> &nbsp;·&nbsp; '
                f'<span style="color:#94a3b8">{n_dis} dismissed</span></div>',
                unsafe_allow_html=True,
            )

        if bugs:
            st.markdown('<div class="sh">Bugs</div>', unsafe_allow_html=True)
            for f in sorted(bugs, key=lambda x: sev_order.get(x.severity.lower(), 9)):
                render_finding(f)

        if ux_issues:
            st.markdown('<div class="sh">UX & Design Issues</div>', unsafe_allow_html=True)
            for f in ux_issues:
                render_finding(f)

        if suggestions:
            st.markdown('<div class="sh">Suggestions</div>', unsafe_allow_html=True)
            for f in suggestions:
                render_finding(f)

        if not total:
            st.markdown('<p style="color:#9ca3af;font-size:14px">No structured findings — check Live Feed tab for agent narration.</p>', unsafe_allow_html=True)

# ── Live Feed ──────────────────────────────────────────────────────────────────

with tab_feed:
    if not st.session_state.conversation:
        st.markdown('<p style="color:#9ca3af;font-size:14px;padding:16px 0">Run the agent to see the live conversation.</p>', unsafe_allow_html=True)
    else:
        for msg in st.session_state.conversation:
            if msg["role"] == "user":
                st.markdown(
                    f'<div class="turn" style="border-left:4px solid #059669">'
                    f'<div style="font-size:11px;font-weight:700;color:#059669;letter-spacing:.07em;text-transform:uppercase;margin-bottom:6px">Tester</div>'
                    f'<div style="font-size:14px;color:#374151;line-height:1.6">{msg["content"]}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                if msg.get("audio"):
                    st.audio(msg["audio"], format="audio/wav")
            else:
                chip = step_chip(msg.get("status", ""))
                step_findings: list[ParsedFinding] = msg.get("findings", [])
                st.markdown(
                    f'<div class="turn" style="border-left:4px solid #2563eb">'
                    f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:8px">'
                    f'<span style="font-size:11px;font-weight:700;color:#2563eb;letter-spacing:.07em;text-transform:uppercase">Step {msg.get("step","")}</span>'
                    f'{chip}</div>'
                    f'<div style="font-size:14px;color:#374151;line-height:1.6">{msg.get("content","")}</div>'
                    f'</div>',
                    unsafe_allow_html=True,
                )
                if msg.get("audio"):
                    st.audio(msg["audio"], format="audio/wav")
                if step_findings:
                    with st.expander(f"{len(step_findings)} finding(s) this step"):
                        for f in step_findings:
                            st.markdown(finding_html(f), unsafe_allow_html=True)

# ── Step Details ───────────────────────────────────────────────────────────────

with tab_steps:
    if result is None:
        st.markdown('<p style="color:#9ca3af;font-size:14px;padding:16px 0">No run data yet.</p>', unsafe_allow_html=True)
    else:
        for step in result.steps:
            icon = {"PASS": "✅", "WARNING": "⚠️", "FAIL": "❌", "DONE": "🏁", "STOPPED": "🛑"}.get(step.status, "❓")
            with st.expander(f"{icon} Step {step.step} · {step.status} · clicked: {step.click_target or 'none'}"):
                ca, cb = st.columns(2)
                ca.markdown(f"**Before**\n\n`{step.before_url}`")
                cb.markdown(f"**After**\n\n`{step.after_url}`")
                if step.agent_narration:
                    st.markdown("**Agent reasoning**")
                    st.markdown(
                        f'<div class="card" style="padding:12px 16px;margin:4px 0">'
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
                    st.markdown("**Findings**")
                    for f in step.findings:
                        st.markdown(finding_html(f), unsafe_allow_html=True)

# ── Report ─────────────────────────────────────────────────────────────────────

with tab_report:
    path: Path | None = None
    if result is not None and result.md_report_path.exists():
        path = result.md_report_path
    elif selected_report_name:
        c = REPORTS_DIR / selected_report_name
        if c.exists():
            path = c
    if path:
        txt = path.read_text(encoding="utf-8")
        st.download_button("⬇ Download report (.md)", data=txt, file_name=path.name, mime="text/markdown")
        st.markdown(f'<div class="card">{txt}</div>', unsafe_allow_html=True)
    else:
        st.markdown('<p style="color:#9ca3af;font-size:14px;padding:16px 0">No report yet.</p>', unsafe_allow_html=True)

# ── Screenshots ────────────────────────────────────────────────────────────────

with tab_shots:
    shots: list[Path] = []
    if result is not None:
        shots = result.screenshots
    elif selected_report_name:
        rid = selected_report_name.replace("run_", "").replace(".md", "")
        d = SCREENSHOTS_DIR / f"run_{rid}"
        if d.exists():
            shots = sorted(d.glob("step_*.png"), key=lambda p: p.name)
    if shots:
        cols = st.columns(min(3, len(shots)))
        for i, s in enumerate(shots):
            with cols[i % len(cols)]:
                st.image(str(s), caption=f"Step {i + 1}", use_container_width=True)
    else:
        st.markdown('<p style="color:#9ca3af;font-size:14px;padding:16px 0">Screenshots appear here after a run.</p>', unsafe_allow_html=True)
