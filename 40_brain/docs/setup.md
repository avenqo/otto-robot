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

## Identify a specific Pico (optional)
`udevadm info -a -n /dev/ttyACM0 | grep serial` — use the value in `ATTRS{serial}==` to pin the rule.

## Deviations / notes
(none yet)
