import time

import pytest

from otto_bridge import Limits, SpineLink
from otto_bridge.fake_spine import FakeSpine


def wait_for(cond, timeout=2.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        if cond():
            return True
        time.sleep(0.02)
    return False


@pytest.fixture
def rig():
    spine = FakeSpine().start()
    link = SpineLink(spine.path, send_hz=20, command_timeout_s=0.3, reconnect_s=0.1)
    link.start()
    yield spine, link
    link.close()
    spine.close()


def test_receives_telemetry(rig):
    spine, link = rig
    assert wait_for(lambda: link.connected)
    assert link.telemetry.heading_deg == pytest.approx(90.0)


def test_free_text_goes_to_log():
    spine = FakeSpine().start()
    seen = []
    link = SpineLink(spine.path, on_log=seen.append)
    link.start()
    try:
        assert wait_for(lambda: link.connected)
        spine.say("WARNING: GY-273 compass (0x1E) not responding")
        assert wait_for(lambda: any("compass" in s for s in seen))
    finally:
        link.close()
        spine.close()


def test_drive_is_resent_and_keeps_watchdog_fed(rig):
    spine, link = rig
    link.set_drive(100, 0)
    # Longer than the 0.5 s firmware watchdog: only resending keeps it moving.
    for _ in range(15):
        link.set_drive(100, 0)
        time.sleep(0.05)
    assert spine.motors == (100.0, 0.0)


def test_stale_target_sends_zero(rig):
    spine, link = rig
    link.set_drive(100, 50)
    assert wait_for(lambda: spine.motors == (100.0, 50.0))
    # Caller stops refreshing: after command_timeout_s the link sends V,0,0.
    assert wait_for(lambda: spine.motors == (0.0, 0.0), timeout=2.0)
    assert spine.lines[-1] == "V,0,0"


def test_limits_are_clamped(rig):
    spine, link = rig
    link.set_drive(10_000, -99_999)
    lim = Limits()
    assert wait_for(lambda: spine.motors == (lim.max_linear_mm_s, -lim.max_angular_mrad_s))


def test_non_finite_rejected(rig):
    _, link = rig
    with pytest.raises(Exception):
        link.set_drive(float("nan"), 0)


def test_close_sends_stop():
    spine = FakeSpine().start()
    link = SpineLink(spine.path, send_hz=20)
    link.start()
    link.set_drive(100, 0)
    assert wait_for(lambda: spine.motors == (100.0, 0.0))
    link.close()
    assert wait_for(lambda: spine.lines[-1] == "V,0,0")
    spine.close()


def test_survives_missing_port():
    link = SpineLink("/dev/does-not-exist", reconnect_s=0.05)
    link.start()
    time.sleep(0.2)
    assert not link.connected
    link.close()


def test_reader_survives_port_closed_underneath(rig):
    spine, link = rig
    assert wait_for(lambda: link.connected)
    link._ser.fd = None  # what pyserial looks like mid-close: read() raises TypeError
    reader = next(t for t in link._threads if t.name == "spine-reader")
    time.sleep(0.3)
    assert reader.is_alive()
    link._close_port()
    assert wait_for(lambda: link.connected, timeout=3.0)  # writer reopens, reader resumes
