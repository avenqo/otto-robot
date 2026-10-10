import pytest

from otto_bridge.commands import CommandMapper, Scaling


class Clock:
    t = 100.0

    def __call__(self):
        return self.t


@pytest.fixture
def m():
    clock = Clock()
    mapper = CommandMapper(Scaling(200.0, 1000.0), axis_timeout_s=0.4, clock=clock)
    mapper.clock = clock
    return mapper


@pytest.mark.parametrize("cmd,expected", [
    ("mf:50", (100.0, 0.0)), ("mb:100", (-200.0, 0.0)),
    ("ml:50", (0.0, 500.0)), ("mr:100", (0.0, -1000.0)),
    ("mf:250", (200.0, 0.0)),  # clamped to 100 %
])
def test_axes(m, cmd, expected):
    assert m.handle(cmd) == "ok"
    assert m.target() == expected


def test_axes_combine_and_last_wins_per_axis(m):
    m.handle("mf:100")
    m.handle("ml:50")
    assert m.target() == (200.0, 500.0)
    m.handle("mb:50")
    assert m.target() == (-100.0, 500.0)


def test_axis_expires_without_refresh(m):
    m.handle("mf:100")
    m.clock.t += 0.3
    assert m.target() == (200.0, 0.0)
    m.clock.t += 0.2
    assert m.target() == (0.0, 0.0)


def test_one_axis_expires_independently(m):
    m.handle("mf:100")
    m.clock.t += 0.3
    m.handle("ml:100")
    m.clock.t += 0.3
    assert m.target() == (0.0, 1000.0)


@pytest.mark.parametrize("stop", ["ms:0", "ms:5", "RESET"])
def test_stop(m, stop):
    m.handle("mf:100")
    m.handle("ml:100")
    assert m.handle(stop) == "ok"
    assert m.target() == (0.0, 0.0)


@pytest.mark.parametrize("cmd", ["HORN", "LIGHT", "SIREN", "TURN_IN_PLACE", "cl", "cu"])
def test_unsupported_does_not_move(m, cmd):
    assert m.handle(cmd) == "unsupported"
    assert m.target() == (0.0, 0.0)


@pytest.mark.parametrize("cmd", ["", "mf", "mf:", "mf:abc", "mf:-5", "mf:1000", "xx:1", "V,100,0", "mf:50;rm"])
def test_invalid_is_ignored(m, cmd):
    assert m.handle(cmd) == "invalid"
    assert m.target() == (0.0, 0.0)


def test_whitespace_and_newline_tolerated(m):
    assert m.handle(" mf:10\r\n") == "ok"
