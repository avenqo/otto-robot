import socket
import time

import pytest

from otto_bridge import SpineLink
from otto_bridge.commands import CommandMapper, Scaling
from otto_bridge.fake_spine import FakeSpine
from otto_bridge.gateway import UdpGateway
from tests.test_link import wait_for


@pytest.fixture
def rig():
    spine = FakeSpine().start()
    link = SpineLink(spine.path, send_hz=20, command_timeout_s=0.3, reconnect_s=0.1)
    link.start()
    gw = UdpGateway(link, CommandMapper(Scaling(200.0, 1000.0), axis_timeout_s=0.3),
                    host="127.0.0.1", port=0, tick_hz=40)
    gw.start()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    yield spine, gw, lambda msg: sock.sendto(msg.encode(), ("127.0.0.1", gw.port))
    sock.close()
    gw.close()
    link.close()
    spine.close()


def test_command_reaches_motors_and_expires(rig):
    spine, _, send = rig
    for _ in range(8):  # the app repeats while the stick is held
        send("mf:50")
        time.sleep(0.05)
    assert spine.motors == (100.0, 0.0)
    # App goes silent -> within axis timeout + link timeout everything stops.
    assert wait_for(lambda: spine.motors == (0.0, 0.0), timeout=2.0)


def test_diagonal_and_stop(rig):
    spine, _, send = rig
    send("mf:100\nml:100")  # two commands in one datagram
    assert wait_for(lambda: spine.motors == (200.0, 1000.0))
    send("ms:0")
    assert wait_for(lambda: spine.motors == (0.0, 0.0))


def test_garbage_is_harmless(rig):
    spine, _, send = rig
    send("\xff\x00 hello")
    send("mf:nan")
    time.sleep(0.2)
    assert spine.motors == (0.0, 0.0)
