"""Serial link to the spine: keeps the firmware watchdog fed and parses telemetry.

The spine stops its motors 500 ms after the last drive command. SpineLink
therefore resends the current target at a fixed rate, but only while the
caller keeps refreshing it (``command_timeout_s``). If the caller goes quiet,
the link sends zero-velocity itself, so a crashed app can never leave Otto
driving on stale input.
"""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass
from typing import Callable

import serial

from .protocol import ProtocolError, Telemetry, format_drive, parse_telemetry

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class Limits:
    """Hard limits applied before anything reaches the wire.

    Defaults match MAX_SPEED_MM_S and TRACK_WIDTH_MM in spine/Config.h
    (377 mm/s; 377 / 100 mm half-track = 3.77 rad/s).
    """

    max_linear_mm_s: float = 377.0
    max_angular_mrad_s: float = 3770.0


class SpineLink:
    def __init__(
        self,
        port: str,
        baud: int = 115200,
        *,
        limits: Limits = Limits(),
        send_hz: float = 10.0,
        command_timeout_s: float = 0.5,
        telemetry_timeout_s: float = 1.0,
        reconnect_s: float = 1.0,
        on_telemetry: Callable[[Telemetry], None] | None = None,
        on_log: Callable[[str], None] | None = None,
    ) -> None:
        self.port = port
        self.baud = baud
        self.limits = limits
        self._period = 1.0 / send_hz
        self._command_timeout = command_timeout_s
        self._telemetry_timeout = telemetry_timeout_s
        self._reconnect = reconnect_s
        self._on_telemetry = on_telemetry
        self._on_log = on_log or (lambda line: log.info("spine: %s", line))

        self._lock = threading.Lock()
        self._target = (0.0, 0.0)
        self._target_at = 0.0
        self._telemetry: Telemetry | None = None
        self._telemetry_at = 0.0
        self._ser: serial.Serial | None = None
        self._warned_bad_telemetry = False
        self._stop = threading.Event()
        self._threads: list[threading.Thread] = []

    # --- public API -------------------------------------------------------

    def start(self) -> None:
        self._stop.clear()
        self._threads = [
            threading.Thread(target=self._writer, name="spine-writer", daemon=True),
            threading.Thread(target=self._reader, name="spine-reader", daemon=True),
        ]
        for t in self._threads:
            t.start()

    def close(self) -> None:
        """Send a stop, then shut the link down."""
        self.stop()
        self._write_now(format_drive(0, 0))
        self._stop.set()
        for t in self._threads:
            t.join(timeout=2.0)
        self._close_port()

    def set_drive(self, linear_mm_s: float, angular_mrad_s: float) -> None:
        """Set the drive target. Must be refreshed within ``command_timeout_s``."""
        format_drive(linear_mm_s, angular_mrad_s)  # validates finiteness
        lin = max(-self.limits.max_linear_mm_s, min(self.limits.max_linear_mm_s, linear_mm_s))
        ang = max(-self.limits.max_angular_mrad_s, min(self.limits.max_angular_mrad_s, angular_mrad_s))
        with self._lock:
            self._target = (lin, ang)
            self._target_at = time.monotonic()

    def stop(self) -> None:
        with self._lock:
            self._target = (0.0, 0.0)
            self._target_at = time.monotonic()

    @property
    def telemetry(self) -> Telemetry | None:
        """Latest telemetry, or None if none arrived within ``telemetry_timeout_s``."""
        with self._lock:
            if self._telemetry is None:
                return None
            if time.monotonic() - self._telemetry_at > self._telemetry_timeout:
                return None
            return self._telemetry

    @property
    def connected(self) -> bool:
        return self.telemetry is not None

    # --- internals --------------------------------------------------------

    def _open_port(self) -> serial.Serial | None:
        with self._lock:
            if self._ser is not None:
                return self._ser
        try:
            ser = serial.Serial(self.port, self.baud, timeout=0.1, write_timeout=0.5)
        except (serial.SerialException, OSError) as exc:
            log.warning("cannot open %s: %s", self.port, exc)
            return None
        log.info("opened %s", self.port)
        with self._lock:
            self._ser = ser
        return ser

    def _close_port(self) -> None:
        with self._lock:
            ser, self._ser = self._ser, None
        if ser is not None:
            try:
                ser.close()
            except (serial.SerialException, OSError):
                pass

    def _write_now(self, data: bytes) -> bool:
        with self._lock:
            ser = self._ser
        if ser is None:
            return False
        try:
            ser.write(data)
            return True
        except (serial.SerialException, OSError, TypeError, ValueError) as exc:
            log.warning("write failed: %s", exc)
            self._close_port()
            return False

    def _writer(self) -> None:
        while not self._stop.is_set():
            if self._open_port() is None:
                self._stop.wait(self._reconnect)
                continue
            with self._lock:
                lin, ang = self._target
                fresh = time.monotonic() - self._target_at <= self._command_timeout
            if not fresh:
                lin = ang = 0.0
            self._write_now(format_drive(lin, ang))
            self._stop.wait(self._period)

    def _reader(self) -> None:
        buf = b""
        while not self._stop.is_set():
            with self._lock:
                ser = self._ser
            if ser is None:
                self._stop.wait(0.1)
                continue
            try:
                chunk = ser.read(256)
            except (serial.SerialException, OSError, TypeError, ValueError) as exc:
                # TypeError/ValueError: the writer closed the port under our feet
                # (pyserial then reads from fd None). Must never kill this thread.
                log.warning("read failed: %s", exc)
                self._close_port()
                buf = b""
                continue
            buf += chunk
            while b"\n" in buf:
                raw, buf = buf.split(b"\n", 1)
                self._handle_line(raw.decode("ascii", errors="replace").strip())
            if len(buf) > 1024:  # no newline in sight: garbage, resync
                buf = b""

    def _handle_line(self, line: str) -> None:
        if not line:
            return
        if line.startswith("T,"):
            try:
                tel = parse_telemetry(line)
            except ProtocolError as exc:
                if not self._warned_bad_telemetry:
                    self._warned_bad_telemetry = True
                    log.warning("dropping malformed telemetry (logged once): %s", exc)
                return
            with self._lock:
                self._telemetry = tel
                self._telemetry_at = time.monotonic()
            if self._on_telemetry:
                self._on_telemetry(tel)
        else:
            self._on_log(line)
