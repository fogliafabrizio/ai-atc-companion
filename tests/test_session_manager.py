import threading
import time

import pytest

from src.session_manager import SessionManager, Transmission
from src.udp_listener import XPlaneState


class StubUDPListener:
    def __init__(self, state: XPlaneState | None = None) -> None:
        self._state = state or XPlaneState()

    def get_state(self) -> XPlaneState:
        return self._state

    def set_state(self, state: XPlaneState) -> None:
        self._state = state

    def start(self) -> None:
        pass

    def stop(self, timeout: float = 2.0) -> None:
        pass


@pytest.fixture
def stub_udp() -> StubUDPListener:
    return StubUDPListener()


@pytest.fixture
def manager(stub_udp: StubUDPListener) -> SessionManager:
    sm = SessionManager(udp_listener=stub_udp, poll_interval=0.05)
    sm.start()
    yield sm
    sm.stop()


class TestUDPStatePolling:
    def test_initial_state_is_default_xplanestate(self, manager: SessionManager) -> None:
        state = manager.get_udp_state()
        assert isinstance(state, XPlaneState)

    def test_state_updates_after_poll_interval(
        self, manager: SessionManager, stub_udp: StubUDPListener
    ) -> None:
        new_state = XPlaneState(altitude_msl_ft=5000.0)
        stub_udp.set_state(new_state)
        time.sleep(0.15)
        assert manager.get_udp_state().altitude_msl_ft == 5000.0

    def test_state_is_a_copy_not_reference(self, manager: SessionManager) -> None:
        a = manager.get_udp_state()
        b = manager.get_udp_state()
        assert a == b
        assert a is not b


class TestTransmissionLog:
    def test_initially_empty(self, manager: SessionManager) -> None:
        assert manager.get_transmissions() == []

    def test_add_pilot_transmission(self, manager: SessionManager) -> None:
        manager.add_transmission("pilot", "ready to copy")
        txs = manager.get_transmissions()
        assert txs[0].role == "pilot"
        assert txs[0].text == "ready to copy"

    def test_add_atc_transmission(self, manager: SessionManager) -> None:
        manager.add_transmission("atc", "Callsign, roger. Standby.")
        assert manager.get_transmissions()[0].role == "atc"

    def test_multiple_transmissions_ordered(self, manager: SessionManager) -> None:
        manager.add_transmission("pilot", "first")
        manager.add_transmission("atc", "second")
        txs = manager.get_transmissions()
        assert txs[0].text == "first"
        assert txs[1].text == "second"

    def test_returned_list_is_a_copy(self, manager: SessionManager) -> None:
        manager.add_transmission("pilot", "test")
        txs = manager.get_transmissions()
        txs.clear()
        assert len(manager.get_transmissions()) == 1

    def test_transmission_has_timestamp(self, manager: SessionManager) -> None:
        before = time.time()
        manager.add_transmission("pilot", "now")
        after = time.time()
        ts = manager.get_transmissions()[0].timestamp
        assert before <= ts <= after


class TestThreadSafety:
    def test_concurrent_add_transmissions_no_data_loss(self, manager: SessionManager) -> None:
        threads = [
            threading.Thread(
                target=lambda: [manager.add_transmission("pilot", f"msg-{i}") for i in range(10)]
            )
            for _ in range(10)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert len(manager.get_transmissions()) == 100

    def test_start_stop_idempotent(self, stub_udp: StubUDPListener) -> None:
        sm = SessionManager(udp_listener=stub_udp, poll_interval=0.05)
        sm.start()
        sm.stop()
        sm.stop()
