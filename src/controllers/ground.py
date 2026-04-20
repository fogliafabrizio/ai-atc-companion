import json
from dataclasses import dataclass

import anthropic

from src.controllers.base import BaseController
from src.session_manager import SessionManager


@dataclass
class GroundContext:
    icao: str
    active_runway: str
    dep_or_arr: str = "departure"  # "departure" | "arrival"


class GroundController(BaseController):
    _SKILL_PATH = "skills/ground_prompt.md"

    def __init__(
        self,
        client: anthropic.Anthropic,
        session: SessionManager,
        context: GroundContext,
        skill_path: str = _SKILL_PATH,
        model: str = BaseController._MODEL,
        freq_map: dict[float, str] | None = None,
    ) -> None:
        super().__init__(client, session, skill_path, model, freq_map)
        self._context = context

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
    ) -> str:
        parking_stand = pilot_str  # already formatted; extract stand separately
        stand = self._session.get_pilot_info().get("parking_stand", "") or "(unknown)"
        return (
            template
            .replace("{{ICAO}}", self._context.icao)
            .replace("{{FILED_RUNWAY}}", self._context.active_runway)
            .replace("{{ACTIVE_RUNWAY}}", active_runway or self._context.active_runway)
            .replace("{{DEP_OR_ARR}}", self._context.dep_or_arr)
            .replace("{{PARKING_STAND}}", stand)
            .replace("{{FREQ_MAP}}", freq_map_str)
            .replace("{{METAR}}", metar)
            .replace("{{PILOT_INFO}}", pilot_str)
            .replace("{{FLIGHT_PLAN}}", fp_str)
            .replace("{{UDP_STATE}}", json.dumps(udp_state.__dict__, default=str, indent=2))
            .replace("{{TRANSMISSION_HISTORY}}", history_lines)
            .replace("{{FLIGHT_PHASE}}", phase_str)
        )
