"""Gemini 3.8 TTS through the Interactions API.

The text is a verbatim transcript; delivery instructions go in speech_metadata.style
so they are not read aloud. A unary request returns a complete WAV (24 kHz mono).
"""
import base64
import os
import wave

TIMEOUT_MS = 120_000
CALL_TIMEOUT_S = 90.0


def client():
    """Gemini client with a request timeout; without one a stalled request hangs the stage forever."""
    from google import genai

    # The SDK's own retry loop sleeps silently on 429/5xx; disable it so common.with_retry
    # sees each failure, logs it, and applies the daily-quota rule.
    return genai.Client(api_key=os.environ["GEMINI_API_KEY"],
                        http_options={"api_version": "v1beta", "timeout": TIMEOUT_MS,
                                      "retry_options": {"attempts": 1}})


def synthesize(client, model: str, text: str, voice: str, style: str = "") -> bytes:
    content = {"type": "text", "text": text}
    if style:
        content["annotations"] = [{"type": "speech_metadata", "style": style}]
    interaction = client.interactions.create(
        model=model,
        input=[{"type": "user_input", "content": [content]}],
        response_format={"type": "audio", "mime_type": "audio/wav"},
        generation_config={"speech_config": [{"voice": voice}]},
        # The client-level timeout bounds each continuation hop; this bounds the whole call.
        timeout=CALL_TIMEOUT_S,
    )
    return base64.b64decode(interaction.output_audio.data)


def wav_seconds(path) -> float:
    with wave.open(str(path)) as w:
        return w.getnframes() / w.getframerate()
