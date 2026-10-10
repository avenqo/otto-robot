import math

import pytest

from otto_bridge import ProtocolError, format_drive, parse_telemetry


def test_format_drive():
    assert format_drive(150.4, -250.6) == b"V,150,-251\n"


@pytest.mark.parametrize("bad", [math.nan, math.inf, -math.inf])
def test_format_drive_rejects_non_finite(bad):
    with pytest.raises(ProtocolError):
        format_drive(bad, 0)
    with pytest.raises(ProtocolError):
        format_drive(0, bad)


def test_parse_telemetry():
    t = parse_telemetry("T,123.4,48.123456,11.654321,1,0,11800\n")
    assert (t.heading_deg, t.lat, t.lon, t.gps_fix, t.radar, t.batt_mv) == (
        123.4, 48.123456, 11.654321, 1, 0, 11800)


def test_parse_telemetry_invalid_heading_is_none():
    assert parse_telemetry("T,-1.0,0,0,0,0,0").heading_deg is None


@pytest.mark.parametrize("line", [
    "", "hello", "T,1,2,3", "T,a,0,0,0,0,0", "T,1,nan,0,0,0,0", "X,1,2,3,4,5,6",
    "T,1,2,3,4,5,6,7",
])
def test_parse_telemetry_rejects(line):
    with pytest.raises(ProtocolError):
        parse_telemetry(line)


def test_nan_heading_keeps_other_fields():
    t = parse_telemetry("T,nan,1.5,2.5,1,0,11000")
    assert t.heading_deg is None and (t.lat, t.lon, t.batt_mv) == (1.5, 2.5, 11000)
