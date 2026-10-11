# Jetson Orin Nano — setup checklist

Target: JetPack 6 (L4T R36.4.7, Ubuntu 22.04.5) → ROS2 **Humble** when it is needed (stage 4+).
Tick items off as you go and note deviations at the bottom.

## 0. Base system
- [ ] `cat /etc/nv_tegra_release` shows R36.x; `lsb_release -a` shows 22.04
- [ ] `sudo apt update && sudo apt upgrade`
- [ ] Power mode: `sudo nvpmodel -q` (and choose deliberately; MAXN = full speed, needs the proper supply — see power topic, tracked separately)
- [ ] Add yourself to the serial group: `sudo usermod -aG dialout $USER`, then log out/in
- [ ] SSH key login enabled, password login optional off
- [ ] Tailscale: `curl -fsSL https://tailscale.com/install.sh | sh && sudo tailscale up`
- [ ] Docker with NVIDIA runtime: `docker info | grep -i runtime` lists `nvidia` (later stages: `jetson-containers`)

## 1. Spine link
1. Plug the RP2040 in. `lsusb` shows `2e8a:…`; `dmesg | tail` shows `ttyACM0`.
2. Install the udev rules (`40_brain/udev/99-otto.rules`; plain config, no execute bit needed). From the repo root:
   ```bash
   sudo cp 40_brain/udev/99-otto.rules /etc/udev/rules.d/
   sudo udevadm control --reload && sudo udevadm trigger
   ls -l /dev/otto-spine      # must exist; replug the Pico if not
   ```
3. Install the bridge:
   ```bash
   sudo apt install python3-venv python3-pip   # if missing
   cd 40_brain/bridge
   python3 -m venv .venv && . .venv/bin/activate
   pip install -e '.[dev]'
   pytest                  # hardware-free tests against a simulated spine
   ```
4. With the robot **on blocks (wheels off the ground)**:
   ```bash
   otto-bridge monitor                          # telemetry should stream
   otto-bridge drive --linear 100 --duration 2  # wheels turn 2 s, then stop
   ```
5. Safety check: kill the process with `kill -9` while driving — the motors must stop within 500 ms (spine watchdog).

## 2. App gateway
1. Webcam: plug in, `ls /dev/video*`; `v4l2-ctl --list-devices` (apt `v4l-utils`) shows which one is the camera.
2. OpenCV: `sudo apt install python3-opencv`, then create the venv with `python3 -m venv --system-site-packages .venv` (recreate if you already made one).
3. Start: `otto-bridge serve`. It uses `/dev/video0` by default, which is the right one when `v4l2-ctl --list-devices` lists the USB webcam first (the second node, e.g. `/dev/video1`, is usually just metadata). Otherwise pass `--camera /dev/videoN`. Check OpenCV first: `python3 -c "import cv2; print(cv2.__version__)"`.
4. From another machine in the WLAN: open `http://<jetson-ip>:8081/stream` in a browser; test commands with
   `printf 'mf:30' | nc -u -w0 <jetson-ip> 4210` (wheels on blocks! it stops by itself after 0.4 s).
5. In the app: *Einstellungen* → IP = Jetson IP, port 4210.
6. Firewall: allow UDP 4210 and TCP 8081 if `ufw` is active.

## Using the venv (every new shell)
`otto-bridge` is installed inside `40_brain/bridge/.venv`, so it only exists as a command while that venv is active. The current directory does not matter.

```bash
source ~/git/otto-robot/40_brain/bridge/.venv/bin/activate   # prompt shows (.venv)
otto-bridge serve
deactivate                                                    # leave the venv
```

Without activating, call it by its full path (this is also what a systemd service has to do, since services have no activated venv):

```bash
~/git/otto-robot/40_brain/bridge/.venv/bin/otto-bridge serve
```

If the venv does not exist yet or the command is missing, redo step 3 of section 1 (`python3 -m venv … && pip install -e '.[dev]'`).

## Identify a specific Pico (optional)

**Why this matters:** `udev/99-otto.rules` currently matches the Pico only by vendor ID (`2e8a`, Raspberry Pi), so *every* RP2040 on the Jetson would get the name `/dev/otto-spine`. That is fine while exactly one is attached. With a second RP2040 (e.g. a board for displays or sensors) both compete for the same name and it points to whichever was plugged in last — possibly the one with no motor driver behind it. Pin the rule to the Pico's unique serial number before adding a second one.

1. Read the serial of the Pico (adjust `ttyACM0` if it is `ttyACM1`):
   ```bash
   udevadm info -a -n /dev/ttyACM0 | grep serial
   ```
   The output lists the whole device chain; take the `ATTRS{serial}` of the Pico itself (usually the first hit, a hex string like `E6614C311B123456`), not the one of the Jetson's USB controller.
2. Add it to the rule in `40_brain/udev/99-otto.rules`:
   ```
   SUBSYSTEM=="tty", ATTRS{idVendor}=="2e8a", ATTRS{serial}=="E6614C311B123456", SYMLINK+="otto-spine", GROUP="dialout", MODE="0660"
   ```
   A second Pico gets its own line with its own serial and its own symlink name.
3. Reinstall and reload as in section 1 (`cp`, `udevadm control --reload`, `udevadm trigger`), replug, and check `ls -l /dev/otto-spine`.

## Deviations / notes
(none yet)
