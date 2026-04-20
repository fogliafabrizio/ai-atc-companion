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

        pilot_str = _format_pilot_info(self._session.get_pilot_info())
        fp_str = _format_flight_plan(self._session.get_flight_plan())

        system_prompt = (
            self._skill_template
            .replace("{{ICAO}}", self._context.icao)
            .replace("{{RUNWAY}}", self._context.active_runway)
            .replace("{{PILOT_INFO}}", pilot_str)
            .replace("{{FLIGHT_PLAN}}", fp_str)
            .replace("{{UDP_STATE}}", json.dumps(udp_state.__dict__, default=str, indent=2))
            .replace("{{TRANSMISSION_HISTORY}}", history_lines)
        )

        messages = [
            {"role": "user" if t.role == "pilot" else "assistant", "content": t.text}
            for t in transmissions
        ]
        messages.append({"role": "user", "content": text})

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


def _format_pilot_info(info: dict[str, str]) -> str:
    if not info.get("callsign"):
        return "Not configured."
    parts = [f"Callsign: {info['callsign']}"]
    if info.get("company"):
        parts.append(f"Spoken company name: {info['company']}")
    return " — ".join(parts)


def _format_flight_plan(fp) -> str:
    if fp is None:
        return "null"
    route = [w.ident for w in fp.waypoints]
    data: dict = {
        "departure": fp.departure or None,
        "arrival": fp.arrival or None,
        "sid": fp.sid or None,
        "dep_runway": fp.dep_runway or None,
        "arr_runway": fp.arr_runway or None,
        "star": fp.star or None,
        "approach": fp.approach or None,
        "cruise_fl": fp.cruise_fl or None,
        "route": route or None,
    }
    return json.dumps({k: v for k, v in data.items() if v is not None}, indent=2)


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
    if merged[0]["role"] != "user":
        merged.insert(0, {"role": "user", "content": "(session start)"})
    return merged
