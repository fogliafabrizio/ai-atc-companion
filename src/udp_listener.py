"""
UDP listener for X-Plane 12 legacy DATA packets and RREF subscriptions.

X-Plane 12 binds several ports in the 49000-range for its own use
(49000, 49001, ...). Use a port well outside that range for data output;
we default to 49100. Each DATA packet has the format:

    Header : b"DATA\\x00"  (5 bytes)
    Groups : N × 36 bytes
               [0:4]   int32 LE  — row/group index
               [4:36]  8 × float32 LE — values[0..7]

DATA rows extracted here:
    Row  3 — speeds          : values[3] = ground speed (kts)
    Row  4 — Mach, VVI, G    : values[2] = vertical speed (fpm)
                               (values[1] is the legacy VVI slot but reports a
                               -999 sentinel in X-Plane 12 — verified empirically
                               against MSL-derived climb rate)
    Row 20 — GPS position    : values[0] = latitude (deg)
                               values[1] = longitude (deg)
                               values[2] = altitude MSL (ft)
                               values[3] = altitude AGL (ft)

RREF subscription (port 49000 → responses on port 49101):
    Dataref sim/cockpit/radios/com1_freq_hz — active COM1 frequency as an
    integer (Hz×100, e.g. 12180 = 121.80 MHz). Polled at 2 Hz; any change
    is surfaced in XPlaneState.com1_freq_mhz.
"""

from __future__ import annotations

import socket
import struct
import threading
import time
from dataclasses import dataclass, field, replace


_HEADER_PREFIX = b"DATA"
_HEADER_LEN = 5  # "DATA" + one separator byte (0x00 in legacy, 0x2A in X-Plane 12)
_GROUP_FORMAT = "<i8f"  # 1 int32 + 8 float32, little-endian
_GROUP_SIZE = struct.calcsize(_GROUP_FORMAT)  # == 36

_ROW_SPEEDS = 3
_ROW_VSPEED = 4
_ROW_GPS = 20

# Aircraft is considered on the ground when AGL is below this threshold.
_ON_GROUND_AGL_FT = 20.0

_RREF_SEND_PORT = 49000
_RREF_RECV_PORT = 49101
_RREF_COM1_DATAREF = b"sim/cockpit/radios/com1_freq_hz"
_RREF_COM1_INDEX = 0
_RREF_POLL_HZ = 2
_RREF_HEADER = b"RREF,"  # comma — response header differs from subscribe header
_RREF_RECORD_FORMAT = "<if"
_RREF_RECORD_SIZE = struct.calcsize(_RREF_RECORD_FORMAT)  # 8


@dataclass
class XPlaneState:
    """Snapshot of X-Plane flight state parsed from DATA and RREF packets."""

    timestamp: float = field(default_factory=time.time)
    latitude: float = 0.0
    longitude: float = 0.0
    altitude_msl_ft: float = 0.0
    altitude_agl_ft: float = 0.0
    vertical_speed_fpm: float = 0.0
    ground_speed_kts: float = 0.0
    on_ground: bool = False
    com1_freq_mhz: float = 0.0


def parse_data_packet(data: bytes) -> XPlaneState | None:
    """
    Parse one X-Plane DATA UDP packet and return an XPlaneState.

    Returns None if the packet does not begin with the expected DATA header
    or is otherwise malformed.
    """
    if not data.startswith(_HEADER_PREFIX) or len(data) < _HEADER_LEN:
        return None

    payload = data[_HEADER_LEN:]
    num_groups = len(payload) // _GROUP_SIZE

    state = XPlaneState()

    for i in range(num_groups):
        chunk = payload[i * _GROUP_SIZE : i * _GROUP_SIZE + _GROUP_SIZE]
        row_index, *values = struct.unpack(_GROUP_FORMAT, chunk)

        if row_index == _ROW_GPS:
            state.latitude = values[0]
            state.longitude = values[1]
            state.altitude_msl_ft = values[2]
            state.altitude_agl_ft = values[3]
        elif row_index == _ROW_VSPEED:
            state.vertical_speed_fpm = values[2]
        elif row_index == _ROW_SPEEDS:
            state.ground_speed_kts = values[3]

    state.on_ground = state.altitude_agl_ft < _ON_GROUND_AGL_FT

    return state


def parse_rref_packet(data: bytes) -> dict[int, float]:
    """
    Parse one X-Plane RREF response packet.

    Returns a dict mapping dataref index → raw float value.
    Returns {} if the header is wrong or the packet is empty.
    Trailing bytes that don't form a complete record are ignored.
    """
    if not data.startswith(_RREF_HEADER):
        return {}
    payload = data[len(_RREF_HEADER):]
    n = len(payload) // _RREF_RECORD_SIZE
    result: dict[int, float] = {}
    for i in range(n):
        chunk = payload[i * _RREF_RECORD_SIZE : (i + 1) * _RREF_RECORD_SIZE]
        idx, val = struct.unpack(_RREF_RECORD_FORMAT, chunk)
        result[idx] = val
    return result


class UDPListener:
    """
    Background threads that listen for X-Plane packets and keep the most-recent
    XPlaneState available for thread-safe reads.

    - DATA thread: binds `port` (default 49100), parses legacy DATA packets.
    - RREF thread: sends a COM1 subscription to X-Plane port 49000 at startup,
      then listens on `rref_port` (default 49101) for RREF responses and updates
      XPlaneState.com1_freq_mhz. Silently degrades when X-Plane is not running.

    Usage::

        listener = UDPListener(port=49100)
        listener.start()
        ...
        state = listener.get_state()
        ...
        listener.stop()
    """

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 49100,
        xplane_host: str = "127.0.0.1",
        rref_port: int = _RREF_RECV_PORT,
    ) -> None:
        self._host = host
        self._port = port
        self._xplane_host = xplane_host
        self._rref_port = rref_port
        self._state: XPlaneState = XPlaneState()
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._rref_thread: threading.Thread | None = None

    def start(self) -> None:
        """Start the DATA and RREF background listener threads."""
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="udp-listener",
            daemon=True,
        )
        self._thread.start()
        self._rref_thread = threading.Thread(
            target=self._run_rref,
            name="rref-listener",
            daemon=True,
        )
        self._rref_thread.start()

    def stop(self, timeout: float = 2.0) -> None:
        """Signal both listeners to stop and wait for threads to exit."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=timeout)
            self._thread = None
        if self._rref_thread is not None:
            self._rref_thread.join(timeout=timeout)
            self._rref_thread = None

    def get_state(self) -> XPlaneState:
        """Return the most-recent XPlaneState (thread-safe copy)."""
        with self._lock:
            return replace(self._state)

    def _run(self) -> None:
        """Main DATA loop: bind the socket and process incoming packets."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.settimeout(1.0)
        try:
            sock.bind((self._host, self._port))
            while not self._stop_event.is_set():
                try:
                    data, _ = sock.recvfrom(65535)
                except socket.timeout:
                    continue
                parsed = parse_data_packet(data)
                if parsed is not None:
                    parsed.timestamp = time.time()
                    with self._lock:
                        self._state = replace(self._state,
                            timestamp=parsed.timestamp,
                            latitude=parsed.latitude,
                            longitude=parsed.longitude,
                            altitude_msl_ft=parsed.altitude_msl_ft,
                            altitude_agl_ft=parsed.altitude_agl_ft,
                            vertical_speed_fpm=parsed.vertical_speed_fpm,
                            ground_speed_kts=parsed.ground_speed_kts,
                            on_ground=parsed.on_ground,
                        )
        finally:
            sock.close()

    def _run_rref(self) -> None:
        """RREF loop: subscribe to COM1 freq and update state on each response."""
        sub_pkt = (
            b"RREF\x00"
            + struct.pack("<ii", _RREF_POLL_HZ, _RREF_COM1_INDEX)
            + _RREF_COM1_DATAREF.ljust(400, b"\x00")
        )
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.settimeout(1.0)
        try:
            sock.bind((self._host, self._rref_port))
            try:
                sock.sendto(sub_pkt, (self._xplane_host, _RREF_SEND_PORT))
            except OSError:
                pass  # X-Plane not running; still enter receive loop
            while not self._stop_event.is_set():
                try:
                    data, _ = sock.recvfrom(65535)
                except socket.timeout:
                    continue
                except OSError:
                    break
                records = parse_rref_packet(data)
                freq_raw = records.get(_RREF_COM1_INDEX)
                if freq_raw is not None and freq_raw > 0:
                    with self._lock:
                        self._state = replace(self._state, com1_freq_mhz=freq_raw / 100.0)
        finally:
            sock.close()


def _load_port_from_settings(path: str = "config/settings.yaml") -> int | None:
    """Return udp.port from the YAML config, or None if unavailable."""
    try:
        import yaml  # lazy import — only needed when run as script
    except ImportError:
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return data.get("udp", {}).get("port")
    except FileNotFoundError:
        return None


if __name__ == "__main__":
    import sys

    # Precedence: CLI arg > settings.yaml > built-in default 49100
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    else:
        port = _load_port_from_settings() or 49100
    print(f"Listening for X-Plane DATA packets on UDP port {port} …")
    print("Press Ctrl-C to stop.\n")

    listener = UDPListener(port=port)
    listener.start()
    try:
        while True:
            s = listener.get_state()
            print(
                f"[{s.timestamp:.1f}] "
                f"lat={s.latitude:.6f}  lon={s.longitude:.6f}  "
                f"MSL={s.altitude_msl_ft:.0f} ft  AGL={s.altitude_agl_ft:.0f} ft  "
                f"VS={s.vertical_speed_fpm:.0f} fpm  GS={s.ground_speed_kts:.1f} kts  "
                f"on_ground={s.on_ground}  COM1={s.com1_freq_mhz:.2f} MHz"
            )
            time.sleep(1.0)
    except KeyboardInterrupt:
        print("\nStopping …")
        listener.stop()
