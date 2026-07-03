"""
CareerPilot AI — Centralized LLM Service (Groq)

This module provides a thin wrapper around the Groq SDK, exposing the same public
interface that the original GeminiService offered. All existing agents import
`GeminiService`, so we retain the class name to avoid changes elsewhere.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, List, Optional

import groq  # Groq SDK

import config
from config import (
    GROQ_API_KEY,
    GROQ_MODEL_DEFAULT,
    GROQ_TEMPERATURE,
    GROQ_MAX_TOKENS,
)

logger = logging.getLogger(__name__)


class GeminiService:
    """Wrapper around the Groq LLM client.

    The public methods mirror the previous Gemini implementation so that the rest
    of the codebase does not need to be updated.
    """

    def __init__(
        self,
        model_name: str = GROQ_MODEL_DEFAULT,
        temperature: float = GROQ_TEMPERATURE,
        max_tokens: int = GROQ_MAX_TOKENS,
    ) -> None:
        if not GROQ_API_KEY:
            raise ValueError(
                "GROQ_API_KEY is not set. Add it to your .env file."
            )
        # Initialise the Groq client
        self.client = groq.Groq(api_key=GROQ_API_KEY)
        self.model_name = model_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        logger.info("GroqService initialised with model: %s", model_name)

    # ── Core Generation ───────────────────────────────────────────────────────

    def _call_chat(self, messages: List[dict], retries: int = 3, delay: float = 2.0) -> str:
        """Low‑level helper that invokes ``client.chat.completions.create``.

        Retries are performed on any exception raised by the SDK.
        """
        for attempt in range(1, retries + 1):
            try:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                )
                return response.choices[0].message.content.strip()
            except Exception as exc:  # pragma: no cover – SDK specific exceptions
                logger.warning(
                    "Groq chat attempt %d/%d failed: %s",
                    attempt,
                    retries,
                    exc,
                )
                if attempt < retries:
                    time.sleep(delay * attempt)
                else:
                    raise RuntimeError(
                        f"Groq API failed after {retries} attempts: {exc}"
                    ) from exc
        return ""

    def generate_text(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        retries: int = 3,
        delay: float = 2.0,
    ) -> str:
        """Generate a plain‑text response from a prompt.

        The optional ``system_instruction`` is sent as a ``system`` role message.
        """
        messages: List[dict] = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})
        return self._call_chat(messages, retries, delay)

    def generate_json(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        retries: int = 3,
        delay: float = 2.0,
    ) -> Any:
        """Generate JSON output and parse it.

        A strict JSON‑only system prompt is appended to increase the likelihood
        that the model returns valid JSON.
        """
        json_system = (
            (system_instruction or "")
            + "\n\nIMPORTANT: Respond ONLY with valid JSON. No markdown, no explanation, no code fences."
        )
        raw = self.generate_text(prompt, system_instruction=json_system, retries=retries, delay=delay)
        raw = raw.strip()
        if raw.startswith("```"):
            lines = raw.split("\n")
            raw = "\n".join(lines[1:-1]) if len(lines) > 2 else raw
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            logger.error("Failed to parse JSON from model. Raw output: %s", raw[:500])
            return raw

    # ── Stateful Chat ────────────────────────────────────────────────────────

    def start_chat(
        self,
        history: Optional[List[dict[str, str]]] = None,
        system_instruction: Optional[str] = None,
    ) -> "GeminiChatSession":
        """Create a new chat session.

        ``history`` should be a list of ``{"role": ..., "content": ...}`` dicts.
        """
        return GeminiChatSession(
            client=self.client,
            model_name=self.model_name,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            history=history,
            system_instruction=system_instruction,
        )

    def chat_with_history(
        self,
        messages: List[dict[str, str]],
        new_message: str,
        system_instruction: Optional[str] = None,
        retries: int = 3,
        delay: float = 2.0,
    ) -> str:
        """One‑shot chat that reconstructs history and sends a new message."""
        session = self.start_chat(history=messages, system_instruction=system_instruction)
        return session.send_message(new_message, retries=retries, delay=delay)

    def switch_model(self, model_name: str) -> None:
        """Hot‑swap the underlying model.

        The Groq client does not need re‑initialisation – we merely store the new
        name for subsequent calls.
        """
        self.model_name = model_name
        logger.info("Switched Groq model to: %s", model_name)


class GeminiChatSession:
    """Thin wrapper around a Groq chat session.

    It maintains an in‑memory list of messages that is sent on each request.
    """

    def __init__(
        self,
        client: groq.Groq,
        model_name: str,
        temperature: float,
        max_tokens: int,
        history: Optional[List[dict[str, str]]] = None,
        system_instruction: Optional[str] = None,
    ) -> None:
        self._client = client
        self._model_name = model_name
        self._temperature = temperature
        self._max_tokens = max_tokens
        # Initialise the message list respecting optional system instruction
        self._messages: List[dict] = []
        if system_instruction:
            self._messages.append({"role": "system", "content": system_instruction})
        if history:
            self._messages.extend(history)

    def send_message(
        self,
        message: str,
        retries: int = 3,
        delay: float = 2.0,
    ) -> str:
        """Send a user message and return the model's reply."""
        self._messages.append({"role": "user", "content": message})
        for attempt in range(1, retries + 1):
            try:
                response = self._client.chat.completions.create(
                    model=self._model_name,
                    messages=self._messages,
                    temperature=self._temperature,
                    max_tokens=self._max_tokens,
                )
                reply = response.choices[0].message.content.strip()
                self._messages.append({"role": "assistant", "content": reply})
                return reply
            except Exception as exc:  # pragma: no cover – SDK specific
                logger.warning(
                    "Chat send_message attempt %d/%d failed: %s",
                    attempt,
                    retries,
                    exc,
                )
                if attempt < retries:
                    time.sleep(delay * attempt)
                else:
                    raise RuntimeError(
                        f"Chat failed after {retries} attempts: {exc}"
                    ) from exc
        return ""

    @property
    def history(self) -> List[dict[str, str]]:
        """Return the current session history (excluding the initial system message)."""
        return list(self._messages)
