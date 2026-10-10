"""Webcam -> HTTP, same URLs the app used for the ESP32-CAM:

  GET /capture   one JPEG
  GET /stream    MJPEG (multipart/x-mixed-replace)
  GET /health    200 once a frame exists

One grab thread serves all clients, so extra viewers cost no extra camera load.
"""

from __future__ import annotations

import logging
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable, Protocol

log = logging.getLogger(__name__)
BOUNDARY = "otto-frame"


class FrameSource(Protocol):
    def read(self) -> bytes | None:
        """Next JPEG frame, or None if the camera failed."""

    def close(self) -> None: ...


class OpenCvSource:
    """USB webcam via OpenCV (``pip install .[camera]`` or apt python3-opencv)."""

    def __init__(self, device: int | str = 0, width: int = 640, height: int = 480, quality: int = 80) -> None:
        import cv2  # imported lazily: the bridge itself must run without OpenCV

        self._cv2 = cv2
        self._quality = quality
        self._cap = cv2.VideoCapture(device, cv2.CAP_V4L2)
        if not self._cap.isOpened():
            raise RuntimeError(f"cannot open camera {device!r}")
        self._cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
        self._cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    def read(self) -> bytes | None:
        ok, frame = self._cap.read()
        if not ok:
            return None
        ok, jpg = self._cv2.imencode(".jpg", frame, [self._cv2.IMWRITE_JPEG_QUALITY, self._quality])
        return jpg.tobytes() if ok else None

    def close(self) -> None:
        self._cap.release()


class CameraServer:
    def __init__(
        self,
        source: FrameSource,
        host: str = "0.0.0.0",
        port: int = 8081,
        fps: float = 15.0,
        reopen: Callable[[], FrameSource] | None = None,
        stale_s: float = 3.0,
    ) -> None:
        self._source = source
        self._reopen = reopen
        self._stale = stale_s
        self._frame_at = 0.0
        self._period = 1.0 / fps
        self._cond = threading.Condition()
        self._frame: bytes | None = None
        self._seq = 0
        self._stop = threading.Event()
        server = self

        class Handler(BaseHTTPRequestHandler):
            timeout = 10  # seconds a client may stall a write/read before its thread is dropped

            timeout = 10  # seconds; also bounds writes to a stalled client
            def log_message(self, fmt, *args):  # quiet: the stream would flood the log
                log.debug("http %s", fmt % args)

            def do_GET(self):
                path = self.path.split("?", 1)[0]
                if path == "/capture":
                    frame = server._latest()
                    if frame is None:
                        self.send_error(503, "no frame yet")
                        return
                    self.send_response(200)
                    self.send_header("Content-Type", "image/jpeg")
                    self.send_header("Content-Length", str(len(frame)))
                    self.send_header("Cache-Control", "no-store")
                    self.end_headers()
                    self.wfile.write(frame)
                elif path == "/stream":
                    self._stream()
                elif path == "/health":
                    self.send_response(200 if server._fresh() else 503)
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                else:
                    self.send_error(404)

            def _stream(self):
                client = f"{self.client_address[0]}:{self.client_address[1]}"
                log.info("stream client connected: %s", client)
                try:
                    self._stream_frames()
                finally:
                    log.info("stream client gone: %s", client)

            def _stream_frames(self):
                self.send_response(200)
                self.send_header("Content-Type", f"multipart/x-mixed-replace; boundary={BOUNDARY}")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                seq = 0
                try:
                    while not server._stop.is_set():
                        frame, seq = server._wait_newer(seq)
                        if frame is None:
                            continue
                        self.wfile.write(
                            f"--{BOUNDARY}\r\nContent-Type: image/jpeg\r\n"
                            f"Content-Length: {len(frame)}\r\n\r\n".encode()
                        )
                        self.wfile.write(frame)
                        self.wfile.write(b"\r\n")
                except (BrokenPipeError, ConnectionResetError, TimeoutError):
                    pass

        self._http = ThreadingHTTPServer((host, port), Handler)
        self._http.daemon_threads = True
        self.port = self._http.server_address[1]
        self._threads = [
            threading.Thread(target=self._grab, name="cam-grab", daemon=True),
            threading.Thread(target=self._http.serve_forever, name="cam-http", daemon=True),
        ]

    def start(self) -> None:
        for t in self._threads:
            t.start()
        log.info("camera HTTP on port %d (/stream, /capture)", self.port)

    def close(self) -> None:
        self._stop.set()
        self._http.shutdown()
        self._http.server_close()
        for t in self._threads:
            t.join(timeout=2.0)
        self._source.close()

    def _latest(self) -> bytes | None:
        with self._cond:
            return self._frame

    def _wait_newer(self, seq: int) -> tuple[bytes | None, int]:
        with self._cond:
            self._cond.wait_for(lambda: self._seq != seq or self._stop.is_set(), timeout=2.0)
            return (self._frame, self._seq) if self._seq != seq else (None, seq)

    def _fresh(self) -> bool:
        with self._cond:
            return self._frame is not None and time.monotonic() - self._frame_at <= self._stale

    def _read_safely(self) -> bytes | None:
        try:
            return self._source.read()
        except Exception:  # e.g. cv2.error: must not kill the grab thread
            log.exception("camera read raised")
            return None

    def _grab(self) -> None:
        next_at = time.monotonic()
        failures = 0
        while not self._stop.is_set():
            frame = self._read_safely()
            if frame is None:
                failures += 1
                if failures == 1:
                    log.warning("camera returned no frame")
                if self._reopen and failures % 30 == 0:  # ~3 s without a frame
                    log.warning("reopening camera after %d failed reads", failures)
                    try:
                        self._source.close()
                        self._source = self._reopen()
                    except Exception:
                        log.exception("reopen failed, will retry")
                self._stop.wait(0.1)
                continue
            if failures:
                log.info("camera recovered after %d failed reads", failures)
            failures = 0
            with self._cond:
                self._frame = frame
                self._frame_at = time.monotonic()
                self._seq += 1
                self._cond.notify_all()
            next_at += self._period
            delay = next_at - time.monotonic()
            if delay > 0:
                self._stop.wait(delay)
            else:
                next_at = time.monotonic()
