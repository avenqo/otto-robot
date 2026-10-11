# hermann_app — Otto remote control

Flutter app: joystick control and live video for Otto. It talks to the `otto-bridge serve` gateway on the Jetson (see [`40_brain/README.md`](../../40_brain/README.md)), not to the RP2040 directly.

## What the app talks to

All in the same WLAN. The Jetson's IP is set in the app (*Einstellungen*).

| Purpose | Protocol | Target |
| --- | --- | --- |
| Drive commands | UDP, plain text (`mf:50`, `ml:30`, `ms:0`, …) | `<jetson-ip>:4210` |
| Live video | HTTP MJPEG | `http://<jetson-ip>:8081/stream` |
| Single photo | HTTP JPEG | `http://<jetson-ip>:8081/capture` |

While the stick is held the app repeats the current command every 100 ms; the gateway stops Otto when commands stop arriving (about 0.4 s). `HORN`, `LIGHT`, `SIREN`, `TURN_IN_PLACE` and camera panning are sent but ignored by the gateway until the spine supports them.

## Requirements

- Flutter SDK with Dart ≥ 3.10.4 (see `pubspec.yaml`), stable channel. Check with `flutter doctor`.
- Android: Android SDK (Android Studio) and a phone with USB debugging enabled.
- Plain HTTP is allowed in the manifests (`usesCleartextTraffic` on Android, `NSAllowsArbitraryLoads` on iOS), otherwise the video stream would be blocked.

## Build and run

From this directory:

```bash
flutter pub get
flutter analyze            # static checks
flutter devices            # phone must be listed
flutter run                # debug build on the connected device, with hot reload
```

Installable Android APK:

```bash
flutter build apk --release
flutter install            # to the connected phone
# result: build/app/outputs/flutter-apk/app-release.apk
```

Other targets: `flutter run -d linux` for a quick desktop test (the video `WebView` does not work there, use a phone), `flutter build ios` (macOS with Xcode only).

## First start

1. Allow the location permission when asked (Android needs it to read the WLAN name).
2. Open *Einstellungen* and enter the Jetson's IP and UDP port `4210`.
3. On the Jetson: `otto-bridge serve` (see [`40_brain/docs/setup.md`](../../40_brain/docs/setup.md)).
4. Test with the robot on blocks first.

## Status

The joystick repeat and the Jetson camera URLs were changed without a Flutter SDK at hand; the first `flutter analyze` and build still have to confirm them. The default IP in `lib/global.dart` (`ROBOT_IP = 192.168.4.1`) is the old ESP32 address and must be changed in the settings.
