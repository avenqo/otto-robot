import http.client

import pytest

from otto_bridge.camera import BOUNDARY, CameraServer
from tests.test_link import wait_for


class FakeSource:
    def __init__(self):
        self.n = 0
        self.closed = False

    def read(self):
        self.n += 1
        return b"\xff\xd8frame%d\xff\xd9" % self.n

    def close(self):
        self.closed = True


class BrokenSource(FakeSource):
    def read(self):
        return None


@pytest.fixture
def cam():
    src = FakeSource()
    server = CameraServer(src, host="127.0.0.1", port=0, fps=100)
    server.start()
    assert wait_for(lambda: server._latest() is not None)
    yield server
    server.close()
    assert src.closed


def get(server, path):
    c = http.client.HTTPConnection("127.0.0.1", server.port, timeout=3)
    c.request("GET", path)
    return c, c.getresponse()


def test_capture(cam):
    c, r = get(cam, "/capture")
    body = r.read()
    assert r.status == 200 and r.getheader("Content-Type") == "image/jpeg"
    assert body.startswith(b"\xff\xd8") and body.endswith(b"\xff\xd9")
    c.close()


def test_stream_delivers_changing_frames(cam):
    c, r = get(cam, "/stream")
    assert r.status == 200 and BOUNDARY in r.getheader("Content-Type")
    seen = set()
    for _ in range(3):
        assert r.fp.readline().strip() == f"--{BOUNDARY}".encode()
        assert r.fp.readline().startswith(b"Content-Type: image/jpeg")
        length = int(r.fp.readline().split(b":")[1])
        r.fp.readline()
        seen.add(r.fp.read(length))
        r.fp.readline()
    assert len(seen) == 3
    c.close()


def test_unknown_path_and_health(cam):
    for path, status in (("/nope", 404), ("/health", 200)):
        c, r = get(cam, path)
        r.read()
        assert r.status == status
        c.close()


def test_no_frame_gives_503():
    server = CameraServer(BrokenSource(), host="127.0.0.1", port=0)
    server.start()
    try:
        for path in ("/capture", "/health"):
            c, r = get(server, path)
            r.read()
            assert r.status == 503
            c.close()
    finally:
        server.close()


class FlakySource(FakeSource):
    """Raises for the first reads, like cv2 does when the USB camera hiccups."""

    def read(self):
        self.n += 1
        if self.n <= 3:
            raise RuntimeError("camera hiccup")
        return super().read()


def test_read_exception_does_not_kill_grab_thread():
    server = CameraServer(FlakySource(), host="127.0.0.1", port=0, fps=100)
    server.start()
    try:
        assert wait_for(lambda: server._latest() is not None, timeout=3.0)
    finally:
        server.close()


def test_camera_is_reopened_after_prolonged_failure():
    reopened = []

    def reopen():
        reopened.append(1)
        return FakeSource()

    server = CameraServer(BrokenSource(), host="127.0.0.1", port=0, fps=100, reopen=reopen)
    server.start()
    try:
        assert wait_for(lambda: server._latest() is not None, timeout=6.0)
        assert reopened
    finally:
        server.close()


def test_health_goes_503_when_frames_stop():
    src = FakeSource()
    server = CameraServer(src, host="127.0.0.1", port=0, fps=100, stale_s=0.3)
    server.start()
    try:
        assert wait_for(server._fresh)
        server._stop.set()  # grab loop ends -> frames get stale
        assert wait_for(lambda: not server._fresh(), timeout=2.0)
        c, r = get(server, "/health")
        r.read()
        assert r.status == 503
        c.close()
    finally:
        server._stop.clear()
        server.close()
