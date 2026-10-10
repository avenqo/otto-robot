"""Line protocol between Jetson and RP2040 (see top-level README.md).

  Jetson -> RP2040:  V,<linear_mm_s>,<angular_mrad_s>\\n
  RP2040 -> Jetson:  T,<heading_deg>,<lat>,<lon>,<gps_fix>,<radar>,<batt_mV>\\n

heading_deg is -1 when the compass read failed; batt_mV is 0 until the
battery sensing is wired up.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


class ProtocolError(ValueError):
    """A line did not match the protocol."""


@dataclass(frozen=True)
class Telemetry:
    heading_deg: float | None  # None = compass invalid
    lat: float
    lon: float
    gps_fix: int
    radar: int
    batt_mv: int


def format_drive(linear_mm_s: float, angular_mrad_s: float) -> bytes:
    """Encode a drive command. Refuses non-finite values (firmware rejects them too)."""
    if not (math.isfinite(linear_mm_s) and math.isfinite(angular_mrad_s)):
        raise ProtocolError("drive values must be finite")
    return f"V,{linear_mm_s:.0f},{angular_mrad_s:.0f}\n".encode("ascii")


def parse_telemetry(line: str) -> Telemetry:
    """Decode a ``T,...`` line. Raises ProtocolError on anything malformed."""
    parts = line.strip().split(",")
    if len(parts) != 7 or parts[0] != "T":
        raise ProtocolError(f"not a telemetry line: {line!r}")
    try:
        heading = float(parts[1])
        lat = float(parts[2])
        lon = float(parts[3])
        gps_fix = int(parts[4])
        radar = int(parts[5])
        batt_mv = int(parts[6])
    except ValueError as exc:
        raise ProtocolError(f"bad field in {line!r}: {exc}") from exc
    if not (math.isfinite(lat) and math.isfinite(lon)):
        raise ProtocolError(f"non-finite field in {line!r}")
    # A failed compass read shows up as -1 (or "nan" on older firmware): keep the rest.
    return Telemetry(
        heading_deg=heading if 0.0 <= heading < 360.0 else None,  # NaN fails this test too
        lat=lat,
        lon=lon,
        gps_fix=gps_fix,
        radar=radar,
        batt_mv=batt_mv,
    )
