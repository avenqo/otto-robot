# 40_brain — Jetson Orin Nano

The `brain` tier of Otto: perception, navigation, app API. It talks to the `spine` (RP2040, see `../30_spine`) over USB serial.

## Plan (stages)

| Stage | Content | Status |
| --- | --- | --- |
| 0 | System setup, udev, Docker, Tailscale — [docs/setup.md](docs/setup.md) | checklist ready |
| 1 | Spine bridge: serial driver, watchdog feeding, telemetry, CLI | implemented, tested against a simulated spine; **not yet run on hardware** |
| 2a | App gateway compatible with the existing Flutter app: UDP commands (port 4210) + webcam as MJPEG over HTTP (port 8081) | implemented, tested without hardware; camera and app **not yet run on the real devices** |
| 2b | New API with telemetry for the app (WebSocket/JSON) | planned |
| 3 | Docker Compose + systemd autostart, emergency stop | planned |
| 4+ | Lidar, SLAM, Nav2, vision (ROS2 Humble) | planned |

## Layout

```
bridge/   Python package `otto_bridge` (protocol, SpineLink, command mapper, UDP gateway, camera server, CLI, fake spine) + tests
udev/     99-otto.rules — stable /dev/otto-spine, /dev/otto-lidar
docs/     setup.md
```

## Bridge in a nutshell

`SpineLink` owns the serial port. The firmware stops the motors 500 ms after the last `V,…` line, so the link resends the current target 10×/s — but only while the caller keeps refreshing it (`command_timeout_s`, default 0.5 s). If the caller (later: the API) dies or goes quiet, the link sends `V,0,0` itself. Speeds are clamped to the firmware limits, non-finite values are rejected, and the port is reopened automatically after a USB drop.

```python
from otto_bridge import SpineLink
link = SpineLink("/dev/otto-spine"); link.start()
link.set_drive(150, 0)        # mm/s, mrad/s — refresh at ≥ 2 Hz
print(link.telemetry)         # None if nothing arrived for 1 s
link.close()                  # sends stop
```

CLI: `otto-bridge monitor | drive --linear 100 --angular 0 --duration 2 | stop` (default port `/dev/otto-spine`).

## App gateway (stage 2a)

Everything runs in one WLAN (Otto and the phone); the app's *Einstellungen* page holds the Jetson's IP.

```bash
otto-bridge serve                      # UDP :4210 + camera HTTP :8081, spine on /dev/otto-spine
otto-bridge serve --camera none        # without webcam
otto-bridge serve --camera /dev/video0 --width 1280 --height 720 --fps 10
```

- **Commands** (UDP, plain text, as before): `mf:<0-100>`, `mb:`, `ml:`, `mr:`, `ms:0`, `RESET`. 100 % = 250 mm/s or 2000 mrad/s (`--max-linear`, `--max-angular`). Each axis (linear / turn) expires 0.4 s after its last command, so **the app must repeat the command at ≥ 5 Hz while the stick is held** (the updated app does, every 100 ms). Silence of any kind ends in a stop. `HORN`, `LIGHT`, `SIREN`, `TURN_IN_PLACE` and camera panning (`cl cr cu cd`) are accepted and ignored until the spine has sound / head servo; each is logged once.
- **Camera**: `http://<jetson>:8081/stream` (MJPEG), `/capture` (single JPEG), `/health`. The webcam is read once and shared by all viewers. OpenCV is optional: `pip install -e '.[camera]'`, or on the Jetson `sudo apt install python3-opencv` and create the venv with `--system-site-packages`.
- **Security**: there is no authentication — anyone in the WLAN can drive Otto. Fine for the garden WLAN, not for an open network. Binding and filtering will be revisited with stage 3.

Develop without hardware: `python -m otto_bridge.fake_spine` prints a pty path; pass it as `--port`.

## Tests

```bash
cd bridge && pip install -e '.[dev]' && pytest
```
