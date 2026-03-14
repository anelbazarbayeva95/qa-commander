"""QA Commander Live Agent — orchestrates Gemini Live session + Playwright.

Connects the Gemini Live multimodal session (vision + audio) with browser
automation to create a real-time QA loop:

  User voice/text command
    → Gemini Live sees screenshot + hears command
    → Agent narrates what it sees (spoken response)
    → Playwright executes the recommended click
    → New screenshot captured
    → Gemini Live sees updated page, continues narration
    → Bug report updated in real time
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright, Page

from gemini_live import LiveTurnResult, run_live_session_sync

PROJECT_ROOT = Path(__file__).resolve().parent.parent
REPORTS_DIR = PROJECT_ROOT / "reports"
SCREENSHOTS_DIR = PROJECT_ROOT / "screenshots"

ALLOWED_ORIGINS_DEFAULT = {"example.com", "www.iana.org"}


@dataclass
class StepRecord:
    step: int
    before_url: str
    after_url: str
    screenshot: str
    click_target: str
    status: str  # PASS | WARNING | FAIL | STOPPED | DONE
    agent_narration: str
    audio_wav: bytes
    console_errors: list[dict] = field(default_factory=list)
    network_failures: list[dict] = field(default_factory=list)
    visual_flags: list[str] = field(default_factory=list)
    error: str = ""


@dataclass
class QARunResult:
    run_id: str
    start_url: str
    steps: list[StepRecord]
    turns: list[LiveTurnResult]
    json_report_path: Path
    md_report_path: Path
    logs: list[str]
    success: bool
    error_message: str = ""

    @property
    def latest_report_path(self) -> Path:
        return self.md_report_path

    @property
    def screenshots(self) -> list[Path]:
        run_dir = SCREENSHOTS_DIR / f"run_{self.run_id}"
        if not run_dir.exists():
            return []
        return sorted(run_dir.glob("step_*.png"), key=lambda p: p.name)

    @property
    def summary(self) -> dict:
        return {
            "total": len(self.steps),
            "pass": sum(1 for s in self.steps if s.status == "PASS"),
            "warning": sum(1 for s in self.steps if s.status == "WARNING"),
            "fail": sum(1 for s in self.steps if s.status == "FAIL"),
            "done": sum(1 for s in self.steps if s.status == "DONE"),
        }


class PlaywrightBrowser:
    """Wrapper around a headless Playwright browser for QA automation."""

    def __init__(self, target_url: str, headless: bool = True):
        self._playwright = None
        self._browser = None
        self.page: Page | None = None
        self.target_url = target_url
        self.headless = headless
        self.console_events: list[dict] = []
        self.network_failures: list[dict] = []

    def start(self) -> None:
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(headless=self.headless)
        self.page = self._browser.new_page()
        self.page.on("console", self._handle_console)
        self.page.on("requestfailed", self._handle_request_failed)
        self.page.goto(self.target_url)
        self.page.wait_for_timeout(2000)

    def stop(self) -> None:
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()

    def screenshot(self, path: str) -> None:
        if self.page:
            self.page.screenshot(path=path)

    def click(self, target_text: str) -> bool:
        """Try to click an element by visible text. Returns True on success."""
        if not self.page:
            return False
        for role in ("link", "button"):
            try:
                loc = self.page.get_by_role(role, name=target_text)  # type: ignore[arg-type]
                loc.first.scroll_into_view_if_needed()
                loc.first.click(timeout=5000)
                self.page.wait_for_timeout(2000)
                return True
            except Exception:
                pass
        try:
            loc = self.page.get_by_text(target_text, exact=False)
            loc.first.scroll_into_view_if_needed()
            loc.first.click(timeout=5000)
            self.page.wait_for_timeout(2000)
            return True
        except Exception:
            return False

    def current_url(self) -> str:
        return self.page.url if self.page else self.target_url

    def drain_console_errors(self, since_index: int) -> list[dict]:
        return [e for e in self.console_events[since_index:] if e["type"] == "error"]

    def drain_network_failures(self, since_index: int) -> list[dict]:
        return self.network_failures[since_index:]

    def _handle_console(self, msg: object) -> None:  # type: ignore[type-arg]
        self.console_events.append(
            {"type": getattr(msg, "type", ""), "text": getattr(msg, "text", "")}
        )

    def _handle_request_failed(self, request: object) -> None:  # type: ignore[type-arg]
        failure = getattr(request, "failure", None)
        if callable(failure):
            failure = failure()
        failure_text = (
            failure.get("errorText", "Unknown") if isinstance(failure, dict) else str(failure or "Unknown")
        )
        self.network_failures.append(
            {
                "url": getattr(request, "url", ""),
                "method": getattr(request, "method", ""),
                "failure_text": failure_text,
            }
        )


def _step_status(
    console_errors: list[dict],
    network_failures: list[dict],
    click_target: str,
    is_done: bool,
    had_error: bool,
) -> str:
    if had_error:
        return "FAIL"
    if is_done:
        return "DONE"
    if not click_target:
        return "STOPPED"
    if network_failures:
        return "WARNING"
    if console_errors:
        return "WARNING"
    return "PASS"


def _write_reports(
    run_id: str,
    start_url: str,
    max_steps: int,
    steps: list[StepRecord],
) -> tuple[Path, Path]:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    json_path = REPORTS_DIR / f"run_{run_id}.json"
    md_path = REPORTS_DIR / f"run_{run_id}.md"

    total = len(steps)
    pass_count = sum(1 for s in steps if s.status == "PASS")
    warn_count = sum(1 for s in steps if s.status == "WARNING")
    fail_count = sum(1 for s in steps if s.status == "FAIL")

    report_dict = {
        "run_id": run_id,
        "start_url": start_url,
        "max_steps": max_steps,
        "summary": {
            "total_steps": total,
            "pass": pass_count,
            "warning": warn_count,
            "fail": fail_count,
        },
        "steps": [
            {
                "step": s.step,
                "before_url": s.before_url,
                "after_url": s.after_url,
                "screenshot": s.screenshot,
                "click_target": s.click_target,
                "status": s.status,
                "agent_narration": s.agent_narration,
                "console_errors": len(s.console_errors),
                "network_failures": len(s.network_failures),
                "visual_flags": s.visual_flags,
                "error": s.error,
            }
            for s in steps
        ],
    }

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report_dict, f, indent=2)

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(f"# QA Commander Live Report — {run_id}\n\n")
        f.write(f"- **URL:** {start_url}\n")
        f.write(f"- **Steps:** {total} / {max_steps}\n")
        f.write(f"- **Pass:** {pass_count} | **Warning:** {warn_count} | **Fail:** {fail_count}\n\n")
        f.write("## Steps\n\n")
        for s in steps:
            status_icon = {"PASS": "✅", "WARNING": "⚠️", "FAIL": "❌", "DONE": "🏁", "STOPPED": "🛑"}.get(
                s.status, "❓"
            )
            f.write(f"### Step {s.step} {status_icon} `{s.status}`\n")
            f.write(f"- **Before URL:** {s.before_url}\n")
            f.write(f"- **Clicked:** `{s.click_target or 'N/A'}`\n")
            f.write(f"- **After URL:** {s.after_url}\n")
            f.write(f"- **Console errors:** {len(s.console_errors)}\n")
            f.write(f"- **Network failures:** {len(s.network_failures)}\n")
            if s.visual_flags:
                for flag in s.visual_flags:
                    f.write(f"- ⚑ {flag}\n")
            if s.agent_narration:
                f.write(f"\n**Agent:** {s.agent_narration}\n")
            if s.error:
                f.write(f"\n> **Error:** {s.error}\n")
            f.write("\n")

    return json_path, md_path


def run_live_agent(
    target_url: str,
    max_steps: int = 3,
    user_audio: bytes | None = None,
    user_text: str | None = None,
    on_turn: callable | None = None,  # type: ignore[type-arg]
    headless: bool = True,
) -> QARunResult:
    """
    Run the full QA Commander Live agent.

    Opens a browser, starts a Gemini Live session, and runs a multi-turn
    QA loop where the agent sees screenshots, hears tester commands, and
    speaks its findings — then executes browser actions via Playwright.
    """
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    screenshot_dir = SCREENSHOTS_DIR / f"run_{run_id}"
    screenshot_dir.mkdir(parents=True, exist_ok=True)

    logs: list[str] = []
    steps: list[StepRecord] = []

    def log(msg: str) -> None:
        logs.append(msg)

    browser = PlaywrightBrowser(target_url, headless=headless)

    try:
        log(f"Starting browser → {target_url}")
        browser.start()

        console_cursor = 0
        network_cursor = 0

        def take_screenshot(step: int) -> str:
            path = str(screenshot_dir / f"step_{step}.png")
            browser.screenshot(path)
            log(f"[Step {step}] Screenshot: {path}")
            return path

        def execute_click(click_target: str) -> bool:
            log(f"[Action] Clicking: {click_target}")
            return browser.click(click_target)

        def handle_turn(step: int, result: LiveTurnResult) -> None:
            nonlocal console_cursor, network_cursor

            before_url = browser.current_url()
            had_error = bool(result.error)

            # Check for out-of-origin navigation
            visual_flags: list[str] = []
            after_url = browser.current_url()
            if after_url != before_url:
                origin = urlparse(after_url).netloc
                if origin and origin not in ALLOWED_ORIGINS_DEFAULT and origin not in urlparse(target_url).netloc:
                    visual_flags.append(f"Navigated outside origin: {origin}")

            console_errs = browser.drain_console_errors(console_cursor)
            net_failures = browser.drain_network_failures(network_cursor)
            console_cursor = len(browser.console_events)
            network_cursor = len(browser.network_failures)

            if console_errs:
                visual_flags.append("Console errors detected.")
            if net_failures:
                visual_flags.append("Network failures detected.")

            screenshot_path = str(screenshot_dir / f"step_{step}.png")
            status = _step_status(
                console_errs,
                net_failures,
                result.click_target,
                result.is_done,
                had_error,
            )

            record = StepRecord(
                step=step,
                before_url=before_url,
                after_url=after_url,
                screenshot=screenshot_path,
                click_target=result.click_target,
                status=status,
                agent_narration=result.text,
                audio_wav=result.audio_wav,
                console_errors=console_errs,
                network_failures=net_failures,
                visual_flags=visual_flags,
                error=result.error,
            )
            steps.append(record)
            log(f"[Step {step}] {status} — {result.click_target or 'no action'}")

            if on_turn:
                on_turn(step, record)

        turns = run_live_session_sync(
            target_url=target_url,
            max_steps=max_steps,
            user_audio=user_audio,
            user_text=user_text,
            screenshot_fn=take_screenshot,
            action_fn=execute_click,
            on_turn=handle_turn,
        )

    except Exception as exc:
        log(f"[ERROR] {exc}")
        return QARunResult(
            run_id=run_id,
            start_url=target_url,
            steps=steps,
            turns=[],
            json_report_path=REPORTS_DIR / f"run_{run_id}.json",
            md_report_path=REPORTS_DIR / f"run_{run_id}.md",
            logs=logs,
            success=False,
            error_message=str(exc),
        )
    finally:
        browser.stop()
        log("Browser closed.")

    json_path, md_path = _write_reports(run_id, target_url, max_steps, steps)
    log(f"Reports saved: {md_path.name}")

    return QARunResult(
        run_id=run_id,
        start_url=target_url,
        steps=steps,
        turns=turns,
        json_report_path=json_path,
        md_report_path=md_path,
        logs=logs,
        success=True,
    )
