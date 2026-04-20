from __future__ import annotations

import json
from abc import ABC, abstractmethod

import anthropic

from src.session_manager import SessionManager


class BaseController(ABC):
    _MODEL = "claude-sonnet-4-6"

    def __init__(
        self,
        client: anthropic.Anthropic,
        session: SessionManager,
        skill_path: str,
        model: str = _MODEL,
        freq_map: dict[float, str] | None = None,
    ) -> None:
        self._client = client
        self._session = session
        self._model = model
        self._freq_map_str = _format_freq_map(freq_map or {})
        with open(skill_path, "r", encoding="utf-8") as f:
            self._skill_template = f.read()

    def respond(self, text: str) -> str:
        from src.flight_phase import infer_phase

        transmissions = self._session.get_transmissions()
        udp_state = self._session.get_udp_state()

        history_lines = "\n".join(
            f"[{t.role.upper()}] {t.text}" for t in transmissions
        ) or "(none)"

        pilot_str = _format_pilot_info(self._session.get_pilot_info())
        fp_str = _format_flight_plan(self._session.get_flight_plan())
        phase_str = infer_phase(udp_state).value
        active_runway = self._session.get_active_runway()
        metar = self._session.get_metar() or "(not available)"

        system_prompt = self._build_system_prompt(
            template=self._skill_template,
            pilot_str=pilot_str,
            fp_str=fp_str,
            udp_state=udp_state,
            history_lines=history_lines,
            phase_str=phase_str,
            freq_map_str=self._freq_map_str,
            active_runway=active_runway,
            metar=metar,
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

    def generate_proactive(self, context: str) -> str | None:
        """Call Claude to produce an unsolicited ATC transmission.

        Returns None if the controller decides no action is warranted.
        """
        from src.flight_phase import infer_phase

        udp_state = self._session.get_udp_state()
        transmissions = self._session.get_transmissions()
        history_lines = "\n".join(
            f"[{t.role.upper()}] {t.text}" for t in transmissions
        ) or "(none)"
        pilot_str = _format_pilot_info(self._session.get_pilot_info())
        fp_str = _format_flight_plan(self._session.get_flight_plan())
        phase_str = infer_phase(udp_state).value
        active_runway = self._session.get_active_runway()
        metar = self._session.get_metar() or "(not available)"

        system_prompt = self._build_system_prompt(
            template=self._skill_template,
            pilot_str=pilot_str,
            fp_str=fp_str,
            udp_state=udp_state,
            history_lines=history_lines,
            phase_str=phase_str,
            freq_map_str=self._freq_map_str,
            active_runway=active_runway,
            metar=metar,
        )

        proactive_instruction = (
            "PROACTIVE TRANSMISSION REQUIRED. "
            "Do NOT wait for the pilot to speak. "
            "Issue a single, concise ATC transmission appropriate to the current situation. "
            "If no transmission is warranted right now, reply with exactly the word: STANDBY"
        )
        messages = [{"role": "user", "content": f"{proactive_instruction}\n\nSituation: {context}"}]

        response = self._client.messages.create(
            model=self._model,
            max_tokens=256,
            system=[{"type": "text", "text": system_prompt, "cache_control": {"type": "ephemeral"}}],
            messages=messages,
        )
        reply = response.content[0].text.strip()
        return None if reply.upper() == "STANDBY" else reply

    @abstractmethod
    def _build_system_prompt(
        self,
        template: str,
        pilot_str: str,
        fp_str: str,
        udp_state: object,
        history_lines: str,
        phase_str: str,
        freq_map_str: str,
        active_runway: str,
        metar: str,
    ) -> str: ...


def _format_freq_map(freq_map: dict[float, str]) -> str:
    if not freq_map:
        return "(not available)"
    return ", ".join(f"{role}: {freq:.3f}" for freq, role in sorted(freq_map.items()))


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
    if not messages:
        return messages
    merged: list[dict] = [messages[0]]
    for msg in messages[1:]:
        if msg["role"] == merged[-1]["role"]:
            merged[-1] = {
                "role": msg["role"],
                "content": merged[-1]["content"] + "\n" + msg["content"],
            }
        else:
            merged.append(msg)
    if merged[0]["role"] != "user":
        merged.insert(0, {"role": "user", "content": "(session start)"})
    return merged
