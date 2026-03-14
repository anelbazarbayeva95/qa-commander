"""Gemini Live API session handler for QA Commander Live.

Provides a real-time multimodal session using the Gemini Live API:
- Sends screenshots (vision / see)
- Sends user audio from microphone (hear)
- Receives spoken agent narration (speak)
- Receives structured findings for report generation (create)
"""

from __future__ import annotations

import asyncio
import io
import os
import wave
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from google import genai
from google.genai import types

LIVE_MODEL = "gemini-2.0-flash-live-001"

OUTPUT_SAMPLE_RATE = 24000
OUTPUT_CHANNELS = 1
OUTPUT_BIT_DEPTH = 16

SYSTEM_INSTRUCTION = """You are QA Commander, an elite AI QA engineer and UX auditor with deep expertise in web usability, accessibility, and interface design best practices.

Your mission: Analyse web interfaces like a senior product designer + QA engineer combined. You are sharp, precise, and professional.

For every screenshot you analyse, you MUST identify:

1. FUNCTIONAL BUGS — things that are broken, missing, or behave incorrectly
   - Broken links, 404 errors, navigation failures
   - Forms that fail to submit or validate incorrectly
   - Buttons/CTAs that do nothing
   - Layout breakage (overflow, overlap, clipping)
   - Console errors or network failures you are informed about

2. UX/UI ISSUES — things that work but create friction or confusion
   - Unclear or missing calls-to-action
   - Poor visual hierarchy (nothing draws the eye)
   - Confusing navigation structure
   - Inconsistent design (mixed fonts, spacing, colors)
   - Too much text, wall-of-text patterns
   - Mobile-unfriendly patterns (tiny tap targets, horizontal scroll)
   - Missing feedback states (loading, success, error)

3. BAD DESIGN PATTERNS — aesthetic and design quality issues
   - Visual clutter and information overload (Craigslist-style dense layouts)
   - Poor typography: wrong font sizes, low contrast, unreadable text, too many font styles
   - Color abuse: clashing colors, excessive color variety, no coherent color system
   - Outdated design aesthetics: table-based layouts, mismatched styles
   - Lack of whitespace: cramped, dense, overwhelming layouts
   - Inconsistent alignment and grid violations
   - Poor spacing rhythm between elements
   - No clear design language or visual identity

4. ACCESSIBILITY ISSUES
   - Low contrast text (below WCAG AA 4.5:1 ratio)
   - Missing focus indicators
   - Images without alt text
   - Forms without labels
   - Small click targets (below 44x44px)

5. UX SUGGESTIONS — actionable improvements
   - Specific, concrete, implementable changes
   - Reference industry standards (Nielsen heuristics, WCAG)

OUTPUT FORMAT — always use this exact structure at the end of your narration:

---FINDINGS---
BUG: [title] | SEVERITY: [Critical/High/Medium/Low] | [one sentence description]
UX_ISSUE: [title] | SEVERITY: [High/Medium/Low] | [one sentence description]
SUGGESTION: [title] | [one sentence actionable recommendation]
---END---
CLICK: [exact visible text of next element to test, or NONE if done]

Keep your spoken narration to 3-5 sentences before the findings block.
Be direct, specific, and actionable — like a real senior QA engineer narrating a review.
"""


@dataclass
class ParsedFinding:
    kind: str        # "bug" | "ux_issue" | "suggestion"
    title: str
    severity: str    # "Critical" | "High" | "Medium" | "Low" | ""
    description: str


@dataclass
class LiveTurnResult:
    text: str = ""
    audio_wav: bytes = b""
    click_target: str = ""
    is_done: bool = False
    error: str = ""
    findings: list[ParsedFinding] = field(default_factory=list)

    @property
    def narration(self) -> str:
        """Return only the spoken part (before ---FINDINGS---)."""
        if "---FINDINGS---" in self.text:
            return self.text.split("---FINDINGS---")[0].strip()
        return self.text.strip()

    @property
    def bugs(self) -> list[ParsedFinding]:
        return [f for f in self.findings if f.kind == "bug"]

    @property
    def ux_issues(self) -> list[ParsedFinding]:
        return [f for f in self.findings if f.kind == "ux_issue"]

    @property
    def suggestions(self) -> list[ParsedFinding]:
        return [f for f in self.findings if f.kind == "suggestion"]


def pcm_to_wav(pcm_data: bytes, sample_rate: int = OUTPUT_SAMPLE_RATE) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(OUTPUT_CHANNELS)
        wf.setsampwidth(OUTPUT_BIT_DEPTH // 8)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_data)
    return buf.getvalue()


def parse_findings(text: str) -> list[ParsedFinding]:
    findings: list[ParsedFinding] = []
    if "---FINDINGS---" not in text:
        return findings

    block = text.split("---FINDINGS---")[1]
    if "---END---" in block:
        block = block.split("---END---")[0]

    for line in block.splitlines():
        line = line.strip()
        if not line:
            continue

        if line.upper().startswith("BUG:"):
            parts = line[4:].split("|")
            title = parts[0].strip() if parts else "Unknown bug"
            severity = "High"
            desc = ""
            for p in parts[1:]:
                p = p.strip()
                if p.upper().startswith("SEVERITY:"):
                    severity = p.split(":", 1)[1].strip()
                else:
                    desc = p
            findings.append(ParsedFinding("bug", title, severity, desc))

        elif line.upper().startswith("UX_ISSUE:"):
            parts = line[9:].split("|")
            title = parts[0].strip() if parts else "UX issue"
            severity = "Medium"
            desc = ""
            for p in parts[1:]:
                p = p.strip()
                if p.upper().startswith("SEVERITY:"):
                    severity = p.split(":", 1)[1].strip()
                else:
                    desc = p
            findings.append(ParsedFinding("ux_issue", title, severity, desc))

        elif line.upper().startswith("SUGGESTION:"):
            parts = line[11:].split("|", 1)
            title = parts[0].strip() if parts else "Suggestion"
            desc = parts[1].strip() if len(parts) > 1 else ""
            findings.append(ParsedFinding("suggestion", title, "", desc))

    return findings


def extract_click(text: str) -> tuple[str, bool]:
    click_target = ""
    is_done = False
    for line in reversed(text.splitlines()):
        line = line.strip()
        if line.upper().startswith("CLICK:"):
            val = line[6:].strip()
            if val.upper() == "NONE":
                is_done = True
            else:
                click_target = val
            break
    return click_target, is_done


async def _run_turn(
    session,
    screenshot_path: str | None = None,
    audio_bytes: bytes | None = None,
    text: str | None = None,
    on_text_chunk: Callable[[str], None] | None = None,
) -> LiveTurnResult:
    result = LiveTurnResult()
    parts: list[types.Part] = []

    if screenshot_path and Path(screenshot_path).exists():
        with open(screenshot_path, "rb") as f:
            img_data = f.read()
        parts.append(
            types.Part(inline_data=types.Blob(mime_type="image/png", data=img_data))
        )

    if audio_bytes:
        parts.append(
            types.Part(inline_data=types.Blob(mime_type="audio/wav", data=audio_bytes))
        )
    elif text:
        parts.append(types.Part(text=text))

    if not parts:
        result.error = "No input for this turn."
        return result

    for i, part in enumerate(parts):
        await session.send(input=part, end_of_turn=(i == len(parts) - 1))

    audio_chunks: list[bytes] = []
    text_chunks: list[str] = []

    async for response in session.receive():
        if response.text:
            text_chunks.append(response.text)
            if on_text_chunk:
                on_text_chunk(response.text)
        if response.data:
            audio_chunks.append(response.data)
        sc = response.server_content
        if sc and sc.turn_complete:
            break

    result.text = "".join(text_chunks)
    if audio_chunks:
        result.audio_wav = pcm_to_wav(b"".join(audio_chunks))

    result.findings = parse_findings(result.text)
    result.click_target, result.is_done = extract_click(result.text)
    return result


async def run_live_qa_session(
    target_url: str,
    max_steps: int,
    user_audio: bytes | None,
    user_text: str | None,
    screenshot_fn: Callable[[int], str],
    action_fn: Callable[[str], bool],
    on_turn: Callable[[int, LiveTurnResult], None],
) -> list[LiveTurnResult]:
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

    config = types.LiveConnectConfig(
        response_modalities=["AUDIO", "TEXT"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Charon")
            )
        ),
        system_instruction=types.Content(
            parts=[types.Part(text=SYSTEM_INSTRUCTION)],
            role="user",
        ),
        input_audio_transcription=types.AudioTranscriptionConfig(),
        output_audio_transcription=types.AudioTranscriptionConfig(),
    )

    results: list[LiveTurnResult] = []

    async with client.aio.live.connect(model=LIVE_MODEL, config=config) as session:
        for step in range(1, max_steps + 1):
            screenshot_path = screenshot_fn(step)

            if step == 1:
                intro = (
                    f"Perform a comprehensive QA and UX audit of: {target_url}\n"
                    "Analyse every visible element for bugs, UX issues, bad design patterns, "
                    "accessibility problems, and suggest concrete improvements.\n"
                )
                if user_text:
                    intro += f"Tester focus area: {user_text}\n"
                result = await _run_turn(
                    session,
                    screenshot_path=screenshot_path,
                    audio_bytes=user_audio,
                    text=intro if not user_audio else None,
                )
            else:
                result = await _run_turn(
                    session,
                    screenshot_path=screenshot_path,
                    text="Continue the QA and UX audit on this updated page. Check all new visible elements thoroughly.",
                )

            results.append(result)
            on_turn(step, result)

            if result.error or result.is_done:
                break

            if result.click_target:
                success = action_fn(result.click_target)
                if not success:
                    fail = await _run_turn(
                        session,
                        text=f"Could not interact with '{result.click_target}'. Log this as a bug and continue auditing.",
                    )
                    results.append(fail)
                    on_turn(step, fail)
                    break

    return results


def run_live_session_sync(
    target_url: str,
    max_steps: int,
    user_audio: bytes | None,
    user_text: str | None,
    screenshot_fn: Callable[[int], str],
    action_fn: Callable[[str], bool],
    on_turn: Callable[[int, LiveTurnResult], None],
) -> list[LiveTurnResult]:
    return asyncio.run(
        run_live_qa_session(
            target_url=target_url,
            max_steps=max_steps,
            user_audio=user_audio,
            user_text=user_text,
            screenshot_fn=screenshot_fn,
            action_fn=action_fn,
            on_turn=on_turn,
        )
    )
