"""Simulated spine on a pseudo-terminal, for tests and hardware-free development.

Mimics the firmware: parses ``V``/``M`` lines, stops the "motors" when no
drive command arrives within the watchdog time, and streams ``T`` telemetry.

    python -m otto_bridge.fake_spine      # prints the pty path to connect to
"""

from __future__ import annotations

import os
import select
import threading
import time
import tty


class FakeSpine:
    def __init__(self, watchdog_s: float = 0.5, telemetry_s: float = 0.1) -> None:
        self._master, slave = os.openpty()
        tty.setraw(slave)
        self.path = os.ttyname(slave)
        self._slave = slave  # keep open so the pty survives client reconnects
        self._watchdog = watchdog_s
        self._telemetry = telemetry_s
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._last_cmd = 0.0
        self._motors = (0.0, 0.0)
        self.lines: list[str] = []
        self.heading = 90.0
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> "FakeSpine":
        self._thread.start()
        return self

    def close(self) -> None:
        self._stop.set()
        self._thread.join(timeout=2.0)
        os.close(self._master)
        os.close(self._slave)

    def say(self, text: str) -> None:
        """Emit a free-text line, like the firmware's help/warning messages."""
        os.write(self._master, text.encode("ascii") + b"\n")

    @property
    def motors(self) -> tuple[float, float]:
        """(linear, angular) currently driven; zero once the watchdog tripped."""
        with self._lock:
            if time.monotonic() - self._last_cmd > self._watchdog:
                return (0.0, 0.0)
            return self._motors

    def _run(self) -> None:
        os.write(self._master, b"=== Here is OTTO ===\n")
        buf = b""
        next_tel = time.monotonic()
        while not self._stop.is_set():
            r, _, _ = select.select([self._master], [], [], 0.02)
            if r:
                try:
                    buf += os.read(self._master, 256)
                except OSError:
                    break
                while b"\n" in buf:
                    raw, buf = buf.split(b"\n", 1)
                    self._handle(raw.decode("ascii", errors="replace").strip())
            if time.monotonic() >= next_tel:
                os.write(self._master, f"T,{self.heading:.1f},0.000000,0.000000,0,0,0\n".encode())
                next_tel += self._telemetry

    def _handle(self, line: str) -> None:
        self.lines.append(line)
        parts = line.split(",")
        if parts[0] == "V" and len(parts) == 3:
            try:
                lin, ang = float(parts[1]), float(parts[2])
            except ValueError:
                return
            with self._lock:
                self._motors = (lin, ang)
                self._last_cmd = time.monotonic()


def main() -> None:
    spine = FakeSpine().start()
    print(f"fake spine on {spine.path} (Ctrl+C to quit)", flush=True)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        spine.close()


if __name__ == "__main__":
    main()
