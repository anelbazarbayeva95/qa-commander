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

# Ensure app/ is on the path so live_agent and gemini_live can be imported
sys.path.insert(0, str(Path(__file__).resolve().parent))

import streamlit as st

from live_agent import QARunResult, StepRecord, run_live_agent

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

# ── Custom CSS ─────────────────────────────────────────────────────────────────

st.markdown(
    """
    <style>
    .agent-msg  { background:#1e2d40; border-left:3px solid #4fa3e0; padding:10px 14px; border-radius:6px; margin:4px 0; }
    .user-msg   { background:#1a2d1a; border-left:3px solid #56c274; padding:10px 14px; border-radius:6px; margin:4px 0; }
    .status-pass    { color:#56c274; font-weight:700; }
    .status-warning { color:#f5a623; font-weight:700; }
    .status-fail    { color:#e05c5c; font-weight:700; }
    .status-done    { color:#4fa3e0; font-weight:700; }
    .metric-card { background:#1a1a2e; border-radius:8px; padding:12px; text-align:center; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Session state initialisation ───────────────────────────────────────────────

if "conversation" not in st.session_state:
    st.session_state.conversation: list[dict] = []
if "run_result" not in st.session_state:
    st.session_state.run_result: QARunResult | None = None
if "running" not in st.session_state:
    st.session_state.running = False

# ── Helpers ────────────────────────────────────────────────────────────────────


def get_report_files() -> list[Path]:
    if not REPORTS_DIR.exists():
        return []
    return sorted(REPORTS_DIR.glob("run_*.md"), key=lambda p: p.stat().st_mtime, reverse=True)


def status_badge(status: str) -> str:
    colours = {
        "PASS": "status-pass",
        "WARNING": "status-warning",
        "FAIL": "status-fail",
        "DONE": "status-done",
        "STOPPED": "status-warning",
    }
    icons = {"PASS": "✅", "WARNING": "⚠️", "FAIL": "❌", "DONE": "🏁", "STOPPED": "🛑"}
    cls = colours.get(status, "")
    icon = icons.get(status, "❓")
    return f'<span class="{cls}">{icon} {status}</span>'


# ── Sidebar ────────────────────────────────────────────────────────────────────

with st.sidebar:
    st.image(
        "https://upload.wikimedia.org/wikipedia/commons/thumb/2/2f/Google-gemini-icon.svg/120px-Google-gemini-icon.svg.png",
        width=40,
    )
    st.title("QA Commander Live")
    st.caption("Powered by Gemini Live API")

    st.divider()
    st.subheader("⚙️ Run Settings")

    target_url = st.text_input("Target URL", value="https://example.com", key="target_url")
    max_steps = st.slider("Max steps", min_value=1, max_value=8, value=3, key="max_steps")

    st.divider()
    st.subheader("🎙️ Voice Command")
    st.caption("Record a QA instruction — the agent will hear and act on it.")
    audio_input = st.audio_input("Speak your test instruction", key="voice_cmd")

    st.divider()
    st.subheader("⌨️ Or type a command")
    text_cmd = st.text_area(
        "Text instruction (used if no audio recorded)",
        placeholder="e.g. Check that all navigation links work",
        key="text_cmd",
        height=80,
    )

    st.divider()
    run_btn = st.button("🚀 Run QA Agent", type="primary", use_container_width=True, disabled=st.session_state.running)

    if st.button("🗑️ Clear conversation", use_container_width=True):
        st.session_state.conversation = []
        st.session_state.run_result = None
        st.rerun()

    st.divider()
    st.subheader("📂 Run History")
    report_files = get_report_files()
    if report_files:
        selected_report_name = st.selectbox(
            "Load previous run",
            [r.name for r in report_files],
            key="history_select",
        )
    else:
        st.info("No previous runs yet.")
        selected_report_name = None

# ── Main panel ─────────────────────────────────────────────────────────────────

st.markdown("## 🔬 QA Commander Live")
st.caption("A multimodal agent that sees, hears, speaks, and creates bug reports in real time.")

# ── Run trigger ────────────────────────────────────────────────────────────────

if run_btn and not st.session_state.running:
    if not os.environ.get("GEMINI_API_KEY"):
        st.error("GEMINI_API_KEY environment variable is not set.")
    else:
        # Extract audio bytes if recorded
        user_audio: bytes | None = None
        if audio_input is not None:
            user_audio = audio_input.read()
            st.session_state.conversation.append(
                {"role": "user", "content": "🎙️ Voice command recorded", "audio": user_audio}
            )
        elif text_cmd.strip():
            st.session_state.conversation.append(
                {"role": "user", "content": f"⌨️ {text_cmd.strip()}"}
            )

        st.session_state.running = True

        # Live conversation placeholder for real-time updates
        conv_placeholder = st.empty()

        def on_turn_callback(step: int, record: StepRecord) -> None:
            """Called after each Gemini Live turn to update conversation."""
            st.session_state.conversation.append(
                {
                    "role": "agent",
                    "step": step,
                    "content": record.agent_narration,
                    "status": record.status,
                    "audio": record.audio_wav,
                    "screenshot": record.screenshot,
                }
            )

        with st.spinner("🔬 QA Agent running — see, hear, speak, create…"):
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
        st.rerun()

# ── Tabs ───────────────────────────────────────────────────────────────────────

tab_conv, tab_logs, tab_report, tab_screenshots = st.tabs(
    ["🤖 Agent Conversation", "📋 Execution Logs", "🐛 QA Report", "📸 Screenshots"]
)

# ── Tab 1: Agent Conversation ──────────────────────────────────────────────────

with tab_conv:
    if not st.session_state.conversation:
        st.info("Run the QA agent to see the live conversation here.")
    else:
        for msg in st.session_state.conversation:
            if msg["role"] == "user":
                st.markdown(
                    f'<div class="user-msg">👤 <strong>Tester</strong><br>{msg["content"]}</div>',
                    unsafe_allow_html=True,
                )
                # Replay recorded voice if available
                if msg.get("audio"):
                    st.audio(msg["audio"], format="audio/wav")
            else:
                step = msg.get("step", "")
                status_html = status_badge(msg.get("status", ""))
                narration = msg.get("content", "")
                st.markdown(
                    f'<div class="agent-msg">🤖 <strong>Agent — Step {step}</strong> {status_html}<br><br>{narration}</div>',
                    unsafe_allow_html=True,
                )
                # Play agent spoken response
                if msg.get("audio"):
                    st.audio(msg["audio"], format="audio/wav")

# ── Tab 2: Execution Logs ──────────────────────────────────────────────────────

with tab_logs:
    result = st.session_state.run_result

    # Load from history if no active result
    if result is None and selected_report_name:
        report_path = REPORTS_DIR / selected_report_name
        if report_path.exists():
            st.markdown(report_path.read_text(encoding="utf-8"))
    elif result is not None:
        st.subheader("Run Summary")

        summ = result.summary
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Total Steps", summ["total"])
        c2.metric("✅ Pass", summ["pass"])
        c3.metric("⚠️ Warning", summ["warning"])
        c4.metric("❌ Fail", summ["fail"])

        st.divider()
        st.subheader("Step Details")

        for step in result.steps:
            icon = {"PASS": "✅", "WARNING": "⚠️", "FAIL": "❌", "DONE": "🏁", "STOPPED": "🛑"}.get(
                step.status, "❓"
            )
            with st.expander(f"{icon} Step {step.step} — {step.status} — clicked: `{step.click_target or 'none'}`"):
                col_a, col_b = st.columns(2)
                col_a.write(f"**Before URL:** {step.before_url}")
                col_b.write(f"**After URL:** {step.after_url}")
                if step.agent_narration:
                    st.write(f"**Agent:** {step.agent_narration}")
                if step.visual_flags:
                    for flag in step.visual_flags:
                        st.warning(flag)
                if step.console_errors:
                    st.error(f"{len(step.console_errors)} console error(s)")
                if step.network_failures:
                    st.warning(f"{len(step.network_failures)} network failure(s)")
                if step.error:
                    st.error(f"Error: {step.error}")

        st.divider()
        st.subheader("Raw Execution Log")
        st.code("\n".join(result.logs), language="text")
    else:
        st.info("Run the QA agent to see execution details.")

# ── Tab 3: QA Report ──────────────────────────────────────────────────────────

with tab_report:
    result = st.session_state.run_result

    if result is not None and result.md_report_path.exists():
        report_text = result.md_report_path.read_text(encoding="utf-8")
        st.download_button(
            "⬇️ Download report (.md)",
            data=report_text,
            file_name=result.md_report_path.name,
            mime="text/markdown",
        )
        st.markdown(report_text)
    elif selected_report_name:
        report_path = REPORTS_DIR / selected_report_name
        if report_path.exists():
            st.markdown(report_path.read_text(encoding="utf-8"))
    else:
        st.info("Run the QA agent to generate a report.")

# ── Tab 4: Screenshots ────────────────────────────────────────────────────────

with tab_screenshots:
    result = st.session_state.run_result

    screenshots: list[Path] = []
    if result is not None:
        screenshots = result.screenshots
    elif selected_report_name:
        run_id = selected_report_name.replace("run_", "").replace(".md", "")
        run_dir = SCREENSHOTS_DIR / f"run_{run_id}"
        if run_dir.exists():
            screenshots = sorted(run_dir.glob("step_*.png"), key=lambda p: p.name)

    if screenshots:
        cols = st.columns(min(3, len(screenshots)))
        for i, shot in enumerate(screenshots):
            with cols[i % len(cols)]:
                st.image(str(shot), caption=shot.name, use_container_width=True)
    else:
        st.info("Screenshots will appear here after a run.")
