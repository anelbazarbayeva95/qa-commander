"""Gemini Live API session handler for QA Commander Live.

Provides a real-time multimodal session using the Gemini Live API:
- Sends screenshots (vision / see)
- Sends user audio from microphone (hear)
- Receives spoken agent narration (speak)
- Receives text analysis for report generation (create)
"""

from __future__ import annotations

import asyncio
import io
import os
import struct
import wave
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from google import genai
from google.genai import types

# Live model supporting audio I/O + vision
LIVE_MODEL = "gemini-2.0-flash-live-001"

# Output audio spec from Gemini Live (raw PCM)
OUTPUT_SAMPLE_RATE = 24000
OUTPUT_CHANNELS = 1
OUTPUT_BIT_DEPTH = 16

SYSTEM_INSTRUCTION = """You are QA Commander, an expert QA testing agent with a sharp eye for bugs and UX issues.

Your role:
- Analyse web interface screenshots to detect bugs, layout issues, broken links, and accessibility problems
- Listen to tester voice instructions and execute them as precise QA tasks
- Narrate your findings clearly and professionally as you work
- Decide which element to interact with next based on what you see

Response format:
- Speak your analysis conversationally — what you see, what you're doing, what you found
- Always end your turn by stating the exact visible text of the next element to click, prefixed with "CLICK: "
- If there is nothing more to test, say "DONE: testing complete"
- Keep narration to 2-4 sentences per turn

Example: "I can see the homepage loaded correctly. The navigation links look intact. There is a prominent call-to-action button. CLICK: Learn More"
"""


@dataclass
class LiveTurnResult:
    """Result from a single Gemini Live turn."""
    text: str = ""
    audio_wav: bytes = b""
    click_target: str = ""  # extracted from CLICK: prefix
    is_done: bool = False
    error: str = ""


def pcm_to_wav(pcm_data: bytes, sample_rate: int = OUTPUT_SAMPLE_RATE) -> bytes:
    """Wrap raw 16-bit mono PCM bytes in a WAV container."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(OUTPUT_CHANNELS)
        wf.setsampwidth(OUTPUT_BIT_DEPTH // 8)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_data)
    return buf.getvalue()


def extract_action(text: str) -> tuple[str, bool]:
    """Parse CLICK: or DONE: directive from agent text."""
    click_target = ""
    is_done = False
    for line in text.splitlines():
        line = line.strip()
        if line.upper().startswith("CLICK:"):
            click_target = line[6:].strip()
        elif line.upper().startswith("DONE:"):
            is_done = True
    return click_target, is_done


async def _run_turn(
    session: genai.types.AsyncLiveSession,  # type: ignore[attr-defined]
    screenshot_path: str | None = None,
    audio_bytes: bytes | None = None,
    text: str | None = None,
    on_text_chunk: Callable[[str], None] | None = None,
) -> LiveTurnResult:
    """Send one turn to the live session and collect the response."""
    result = LiveTurnResult()

    # Build the list of parts to send
    parts: list[types.Part] = []

    if screenshot_path and Path(screenshot_path).exists():
        with open(screenshot_path, "rb") as f:
            img_data = f.read()
        parts.append(
            types.Part(
                inline_data=types.Blob(mime_type="image/png", data=img_data)
            )
        )

    if audio_bytes:
        parts.append(
            types.Part(
                inline_data=types.Blob(mime_type="audio/wav", data=audio_bytes)
            )
        )
    elif text:
        parts.append(types.Part(text=text))

    if not parts:
        result.error = "No input provided for this turn."
        return result

    # Send all parts; mark end_of_turn on the last one
    for i, part in enumerate(parts):
        is_last = i == len(parts) - 1
        await session.send(input=part, end_of_turn=is_last)

    # Collect streamed response
    audio_chunks: list[bytes] = []
    text_chunks: list[str] = []

    async for response in session.receive():
        # Text chunk
        if response.text:
            text_chunks.append(response.text)
            if on_text_chunk:
                on_text_chunk(response.text)

        # Audio chunk (raw PCM from Gemini)
        if response.data:
            audio_chunks.append(response.data)

        # Server signals end of its turn
        sc = response.server_content
        if sc and sc.turn_complete:
            break

    result.text = "".join(text_chunks)
    if audio_chunks:
        raw_pcm = b"".join(audio_chunks)
        result.audio_wav = pcm_to_wav(raw_pcm)

    result.click_target, result.is_done = extract_action(result.text)
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
    """
    Run a full QA session using a single persistent Gemini Live connection.

    Args:
        target_url: The website URL being tested.
        max_steps: Maximum interaction steps.
        user_audio: Optional WAV bytes from the tester's microphone.
        user_text: Optional text command if no audio.
        screenshot_fn: Callable(step) -> screenshot_path. Called before each turn.
        action_fn: Callable(click_target) -> success. Executes the click in browser.
        on_turn: Callback(step, result) called after each turn for live UI updates.

    Returns:
        List of LiveTurnResult, one per turn.
    """
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
            # Capture screenshot before this turn
            screenshot_path = screenshot_fn(step)

            if step == 1:
                # First turn: include user command + initial screenshot
                intro = (
                    f"I need you to perform QA testing on: {target_url}\n"
                )
                if user_text:
                    intro += f"Tester instruction: {user_text}\n"
                intro += "Analyse the screenshot and begin testing."

                result = await _run_turn(
                    session,
                    screenshot_path=screenshot_path,
                    audio_bytes=user_audio,
                    text=intro if not user_audio else None,
                )
            else:
                # Subsequent turns: send new screenshot for continued analysis
                result = await _run_turn(
                    session,
                    screenshot_path=screenshot_path,
                    text="Continue QA testing. Analyse this new screenshot.",
                )

            results.append(result)
            on_turn(step, result)

            if result.error or result.is_done:
                break

            if result.click_target:
                success = action_fn(result.click_target)
                if not success:
                    # Inform agent the click failed
                    fail_result = await _run_turn(
                        session,
                        text=f"The click on '{result.click_target}' failed. Suggest an alternative.",
                    )
                    results.append(fail_result)
                    on_turn(step, fail_result)
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
    """Synchronous wrapper around the async live session (for Streamlit)."""
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
