"""Command-line tool for bring-up: ``otto-bridge monitor|drive|stop``."""

from __future__ import annotations

import argparse
import logging
import signal
import threading
import time

from .spine import SpineLink

DEFAULT_PORT = "/dev/otto-spine"


def _monitor(link: SpineLink, args: argparse.Namespace) -> None:
    while True:
        tel = link.telemetry
        print(tel if tel else "no telemetry", flush=True)
        time.sleep(0.5)


def _drive(link: SpineLink, args: argparse.Namespace) -> None:
    end = time.monotonic() + args.duration
    while time.monotonic() < end:
        link.set_drive(args.linear, args.angular)
        time.sleep(0.1)
    link.stop()


def _stop(link: SpineLink, args: argparse.Namespace) -> None:
    link.stop()
    time.sleep(0.3)  # let the writer send at least one V,0,0


def _serve(link: SpineLink, args: argparse.Namespace) -> None:
    from .camera import CameraServer, OpenCvSource
    from .commands import CommandMapper, Scaling
    from .gateway import UdpGateway

    mapper = CommandMapper(Scaling(args.max_linear, args.max_angular))
    gateway = UdpGateway(link, mapper, port=args.udp_port)
    gateway.start()
    camera = None
    if args.camera != "none":
        device = int(args.camera) if args.camera.isdigit() else args.camera
        try:
            camera = CameraServer(OpenCvSource(device, args.width, args.height), port=args.http_port, fps=args.fps)
            camera.start()
        except (ImportError, RuntimeError) as exc:
            logging.getLogger(__name__).error("camera disabled: %s", exc)
    done = threading.Event()
    for sig in (signal.SIGINT, signal.SIGTERM):
        signal.signal(sig, lambda *_: done.set())
    try:
        done.wait()
    finally:
        gateway.close()
        if camera:
            camera.close()


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(prog="otto-bridge")
    p.add_argument("--port", default=DEFAULT_PORT)
    p.add_argument("-v", "--verbose", action="store_true")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("monitor", help="print telemetry until Ctrl+C").set_defaults(fn=_monitor)
    d = sub.add_parser("drive", help="drive for a fixed time, then stop")
    d.add_argument("--linear", type=float, default=0.0, help="mm/s")
    d.add_argument("--angular", type=float, default=0.0, help="mrad/s")
    d.add_argument("--duration", type=float, default=2.0, help="seconds")
    d.set_defaults(fn=_drive)
    sub.add_parser("stop", help="send a stop").set_defaults(fn=_stop)
    s = sub.add_parser("serve", help="run the app gateway (UDP commands + camera)")
    s.add_argument("--udp-port", type=int, default=4210)
    s.add_argument("--http-port", type=int, default=8081)
    s.add_argument("--camera", default="0", help="V4L2 index/path, or 'none'")
    s.add_argument("--width", type=int, default=640)
    s.add_argument("--height", type=int, default=480)
    s.add_argument("--fps", type=float, default=15.0)
    s.add_argument("--max-linear", type=float, default=250.0, help="mm/s at 100%% joystick")
    s.add_argument("--max-angular", type=float, default=2000.0, help="mrad/s at 100%% joystick")
    s.set_defaults(fn=_serve)
    args = p.parse_args(argv)

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO)
    link = SpineLink(args.port)
    link.start()
    try:
        args.fn(link, args)
    except KeyboardInterrupt:
        pass
    finally:
        link.close()


if __name__ == "__main__":
    main()
