"""UDP gateway: receives the legacy app commands and drives the spine."""

from __future__ import annotations

import logging
import socket
import threading

from .commands import CommandMapper
from .spine import SpineLink

log = logging.getLogger(__name__)


class UdpGateway:
    def __init__(
        self,
        link: SpineLink,
        mapper: CommandMapper | None = None,
        host: str = "0.0.0.0",
        port: int = 4210,
        tick_hz: float = 20.0,
    ) -> None:
        self.link = link
        self.mapper = mapper or CommandMapper()
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.bind((host, port))
        self._sock.settimeout(0.1)
        self.port = self._sock.getsockname()[1]
        self._period = 1.0 / tick_hz
        self._stop = threading.Event()
        self._threads: list[threading.Thread] = []
        self._warned: set[str] = set()
        self._last_sender: str | None = None

    def start(self) -> None:
        self._threads = [
            threading.Thread(target=self._receive, name="udp-rx", daemon=True),
            threading.Thread(target=self._tick, name="udp-tick", daemon=True),
        ]
        for t in self._threads:
            t.start()
        log.info("UDP gateway listening on port %d", self.port)

    def close(self) -> None:
        self._stop.set()
        for t in self._threads:
            t.join(timeout=2.0)
        self._sock.close()

    def _receive(self) -> None:
        while not self._stop.is_set():
            try:
                data, addr = self._sock.recvfrom(512)
            except socket.timeout:
                continue
            except OSError:
                break
            sender = f"{addr[0]}:{addr[1]}"
            if sender != self._last_sender:
                log.info("commands from %s", sender)
                self._last_sender = sender
            for line in data.decode("ascii", errors="replace").splitlines():
                if not line.strip():
                    continue
                result = self.mapper.handle(line)
                if result != "ok" and line.strip() not in self._warned:
                    self._warned.add(line.strip())  # once per distinct command
                    log.warning("%s command: %r", result, line.strip())

    def _tick(self) -> None:
        # Feeds SpineLink continuously: expired axes turn into explicit zeros.
        while not self._stop.is_set():
            self.link.set_drive(*self.mapper.target())
            self._stop.wait(self._period)
