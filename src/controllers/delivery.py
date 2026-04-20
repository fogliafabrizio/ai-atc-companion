import json
from dataclasses import dataclass

import anthropic

from src.session_manager import SessionManager


@dataclass
class DeliveryContext:
    icao: str
    active_runway: str


class DeliveryController:
    _SKILL_PATH = "skills/controller_prompt.md"
    _MODEL = "claude-sonnet-4-6"

    def __init__(
        self,
        client: anthropic.Anthropic,
        session: SessionManager,
        context: DeliveryContext,
        skill_path: str = _SKILL_PATH,
        model: str = _MODEL,
    ) -> None:
        self._client = client
        self._session = session
        self._context = context
        self._model = model
        with open(skill_path, "r", encoding="utf-8") as f:
            self._skill_template = f.read()

    def respond(self, text: str) -> str:
        transmissions = self._session.get_transmissions()
        udp_state = self._session.get_udp_state()

        history_lines = "\n".join(
            f"[{t.role.upper()}] {t.text}" for t in transmissions
        ) or "(none)"

        system_prompt = (
            self._skill_template
            .replace("{{ICAO}}", self._context.icao)
            .replace("{{RUNWAY}}", self._context.active_runway)
            .replace("{{UDP_STATE}}", json.dumps(udp_state.__dict__, default=str, indent=2))
            .replace("{{TRANSMISSION_HISTORY}}", history_lines)
        )

        messages = [
            {"role": "user" if t.role == "pilot" else "assistant", "content": t.text}
            for t in transmissions
        ]
        messages.append({"role": "user", "content": text})

        # Ensure messages alternate properly (Anthropic requires user/assistant alternation)
        messages = _enforce_alternation(messages)

        response = self._client.messages.create(
            model=self._model,
            max_tokens=512,
            system=[
                {
                    "type": "text",
                    "text": system_prompt,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=messages,
        )
        return response.content[0].text


def _enforce_alternation(messages: list[dict]) -> list[dict]:
    """Merge consecutive same-role messages so the list strictly alternates user/assistant."""
    if not messages:
        return messages
    merged: list[dict] = [messages[0]]
    for msg in messages[1:]:
        if msg["role"] == merged[-1]["role"]:
            merged[-1] = {"role": msg["role"], "content": merged[-1]["content"] + "\n" + msg["content"]}
        else:
            merged.append(msg)
    # Anthropic requires the first message to be from the user
    if merged[0]["role"] != "user":
        merged.insert(0, {"role": "user", "content": "(session start)"})
    return merged
