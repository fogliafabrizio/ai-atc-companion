from __future__ import annotations

import threading
from typing import TYPE_CHECKING

from src.flight_phase import FlightPhase, infer_phase

if TYPE_CHECKING:
    from src.audio_pipeline import AudioPipeline
    from src.controller_router import ControllerRouter
    from src.session_manager import SessionManager

# (from_phase, to_phase) → context message sent to the active controller
_TRIGGER_TABLE: dict[tuple[FlightPhase, FlightPhase], str] = {
    (FlightPhase.TAXI, FlightPhase.TAKEOFF): (
        "The aircraft has begun its takeoff roll. "
        "If takeoff clearance has not been issued yet, issue it now (include runway and wind). "
        "If already cleared, no action needed — reply STANDBY."
    ),
    (FlightPhase.TAKEOFF, FlightPhase.CLIMB): (
        "The aircraft has just become airborne and is climbing. "
        "Issue the frequency transfer to departure control."
    ),
    (FlightPhase.CLIMB, FlightPhase.CRUISE): (
        "The aircraft has levelled off at cruise altitude. "
        "If you are departure control, issue the handoff to en-route centre now."
    ),
    (FlightPhase.DESCENT, FlightPhase.APPROACH): (
        "The aircraft is entering the approach phase. "
        "If you are approach control, issue initial approach instructions."
    ),
    (FlightPhase.APPROACH, FlightPhase.LANDING): (
        "The aircraft is on final approach. "
        "If landing clearance has not been issued, issue it now (include runway and wind)."
    ),
    (FlightPhase.LANDING, FlightPhase.TAXI): (
        "The aircraft has landed and vacated the runway. "
        "Issue the frequency transfer to ground control."
    ),
}


class ProactiveATCMonitor:
    def __init__(
        self,
        session: SessionManager,
        router: ControllerRouter,
        pipeline: AudioPipeline,
        poll_interval: float = 1.0,
        enabled: bool = True,
    ) -> None:
        self._session = session
        self._router = router
        self._pipeline = pipeline
        self._poll_interval = poll_interval
        self._enabled = enabled
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._last_phase: FlightPhase | None = None
        self._fired: set[tuple[FlightPhase, FlightPhase]] = set()

    def start(self) -> None:
        if not self._enabled:
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self, timeout: float = 2.0) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout)

    def _loop(self) -> None:
        while not self._stop_event.is_set():
            self._stop_event.wait(self._poll_interval)
            if self._stop_event.is_set():
                break
            try:
                self._tick()
            except Exception as exc:
                print(f"[ProactiveATCMonitor] Error: {exc}")

    def _tick(self) -> None:
        udp_state = self._session.get_udp_state()
        current_phase = infer_phase(udp_state)

        if self._last_phase is None:
            self._last_phase = current_phase
            return

        if current_phase == self._last_phase:
            return

        transition = (self._last_phase, current_phase)
        self._last_phase = current_phase

        context_msg = _TRIGGER_TABLE.get(transition)
        if context_msg is None:
            return
        if transition in self._fired:
            return
        if self._pipeline.is_busy():
            return

        controller = self._router.active_controller()
        if controller is None:
            return

        self._fired.add(transition)
        print(f"[ProactiveATCMonitor] Transition {transition[0].value} → {transition[1].value}: triggering proactive transmission.")
        threading.Thread(target=self._transmit, args=(controller, context_msg), daemon=True).start()

    def _transmit(self, controller: object, context: str) -> None:
        try:
            reply = controller.generate_proactive(context)
            if reply is None:
                return
            print(f"[ATC/proactive] {reply}")
            self._session.add_transmission("atc", reply)
            audio_bytes = self._pipeline.synthesize(reply)
            self._pipeline.play_atc(audio_bytes)
        except Exception as exc:
            print(f"[ProactiveATCMonitor] Transmission error: {exc}")
