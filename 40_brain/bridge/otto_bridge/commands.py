"""Maps the legacy app commands (UDP, plain text) onto drive targets.

The Flutter app sends one command per joystick event:

  mf:<0-100>  forward      mb:<0-100>  backward
  ml:<0-100>  turn left    mr:<0-100>  turn right
  ms:<n>      stop

Each axis (linear, angular) remembers its last command and expires when it is
not refreshed within ``axis_timeout_s``. A command that stops arriving - a
released joystick, a dead WLAN, a crashed app - therefore always ends in a
stop, never in a Otto that keeps driving on its last word. The app has to
repeat its command at >= 5 Hz while the stick is held.
"""

from __future__ import annotations

import re
import threading
import time
from dataclasses import dataclass
from typing import Callable

_MOVE = re.compile(r"^(m[fblr]):(\d{1,3})$")
_STOP = re.compile(r"^ms:\d{1,3}$")
# Accepted so the app doesn't see errors, but nothing in the spine implements them yet.
UNSUPPORTED = frozenset({"HORN", "LIGHT", "SIREN", "TURN_IN_PLACE", "cl", "cr", "cu", "cd"})


@dataclass(frozen=True)
class Scaling:
    """What 100 % on the joystick means. Deliberately below the firmware maximum."""

    max_linear_mm_s: float = 250.0
    max_angular_mrad_s: float = 2000.0


class CommandMapper:
    def __init__(
        self,
        scaling: Scaling = Scaling(),
        axis_timeout_s: float = 0.4,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.scaling = scaling
        self._timeout = axis_timeout_s
        self._clock = clock
        self._lock = threading.Lock()
        self._linear = (0.0, 0.0)  # (value, timestamp)
        self._angular = (0.0, 0.0)

    def handle(self, text: str) -> str:
        """Apply one command. Returns 'ok', 'unsupported' or 'invalid'."""
        text = text.strip()
        now = self._clock()
        m = _MOVE.match(text)
        if m:
            percent = min(int(m.group(2)), 100) / 100.0
            kind = m.group(1)
            with self._lock:
                if kind == "mf":
                    self._linear = (percent * self.scaling.max_linear_mm_s, now)
                elif kind == "mb":
                    self._linear = (-percent * self.scaling.max_linear_mm_s, now)
                elif kind == "ml":  # omega > 0 = counter-clockwise, see spine kinematics
                    self._angular = (percent * self.scaling.max_angular_mrad_s, now)
                else:  # mr
                    self._angular = (-percent * self.scaling.max_angular_mrad_s, now)
            return "ok"
        if _STOP.match(text) or text == "RESET":
            with self._lock:
                self._linear = self._angular = (0.0, 0.0)
            return "ok"
        if text in UNSUPPORTED:
            return "unsupported"
        return "invalid"

    def target(self) -> tuple[float, float]:
        """Current (linear_mm_s, angular_mrad_s); expired axes count as zero."""
        now = self._clock()
        with self._lock:
            lin = self._linear[0] if now - self._linear[1] <= self._timeout else 0.0
            ang = self._angular[0] if now - self._angular[1] <= self._timeout else 0.0
        return lin, ang
