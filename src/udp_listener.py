"""
UDP listener for X-Plane 12 legacy DATA packets.

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
"""

from __future__ import annotations

import socket
import struct
import threading
import time
from dataclasses import dataclass, field


_HEADER_PREFIX = b"DATA"
_HEADER_LEN = 5  # "DATA" + one separator byte (0x00 in legacy, 0x2A in X-Plane 12)
_GROUP_FORMAT = "<i8f"  # 1 int32 + 8 float32, little-endian
_GROUP_SIZE = struct.calcsize(_GROUP_FORMAT)  # == 36

_ROW_SPEEDS = 3
_ROW_VSPEED = 4
_ROW_GPS = 20

# Aircraft is considered on the ground when AGL is below this threshold.
# NOTE: This is a heuristic — X-Plane's dedicated on-ground flag requires the
# newer RREF protocol. 20 ft covers normal touchdown plus shallow final flare.
_ON_GROUND_AGL_FT = 20.0


@dataclass
class XPlaneState:
    """Snapshot of X-Plane flight state parsed from a single DATA packet."""

    timestamp: float = field(default_factory=time.time)
    latitude: float = 0.0
    longitude: float = 0.0
    altitude_msl_ft: float = 0.0
    altitude_agl_ft: float = 0.0
    vertical_speed_fpm: float = 0.0
    ground_speed_kts: float = 0.0
    on_ground: bool = False


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

    # Derive on_ground heuristically from AGL altitude.
    # See module docstring for caveats.
    state.on_ground = state.altitude_agl_ft < _ON_GROUND_AGL_FT

    return state


class UDPListener:
    """
    Background thread that listens for X-Plane DATA packets on a UDP port
    and keeps the most-recent XPlaneState available for thread-safe reads.

    Usage::

        listener = UDPListener(port=49100)
        listener.start()
        ...
        state = listener.get_state()
        ...
        listener.stop()
    """

    def __init__(self, host: str = "0.0.0.0", port: int = 49100) -> None:
        self._host = host
        self._port = port
        self._state: XPlaneState = XPlaneState()
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        """Start the background listener thread."""
        if self._thread is not None and self._thread.is_alive():
            return  # already running
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            name="udp-listener",
            daemon=True,
        )
        self._thread.start()

    def stop(self, timeout: float = 2.0) -> None:
        """Signal the listener to stop and wait for the thread to exit."""
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=timeout)
            self._thread = None

    def get_state(self) -> XPlaneState:
        """Return the most-recent XPlaneState (thread-safe copy)."""
        with self._lock:
            s = self._state
            return XPlaneState(
                timestamp=s.timestamp,
                latitude=s.latitude,
                longitude=s.longitude,
                altitude_msl_ft=s.altitude_msl_ft,
                altitude_agl_ft=s.altitude_agl_ft,
                vertical_speed_fpm=s.vertical_speed_fpm,
                ground_speed_kts=s.ground_speed_kts,
                on_ground=s.on_ground,
            )

    def _run(self) -> None:
        """Main loop: bind the socket and process incoming packets."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.settimeout(1.0)  # allows stop_event to be checked each second
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
                        self._state = parsed
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
                f"on_ground={s.on_ground}"
            )
            time.sleep(1.0)
    except KeyboardInterrupt:
        print("\nStopping …")
        listener.stop()
