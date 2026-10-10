import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'dart:math' as math;

import 'package:flutter/material.dart';
import 'package:flutter_joystick/flutter_joystick.dart';
import 'package:http/http.dart' as http;
import 'package:logger/logger.dart';
import 'package:provider/provider.dart';
import 'package:udp/udp.dart';
import 'package:webview_flutter/webview_flutter.dart';

import '../settings/settings_provider.dart';
import '../global.dart';

class ControlPage extends StatefulWidget {
  const ControlPage({super.key});

  @override
  State<ControlPage> createState() => _ControlPageState();
}

class _ControlPageState extends State<ControlPage> {
  final logger = Logger();

  // =========================
  // SAFE STATE (NO LATE)
  // =========================
  String? _receiverIp;
  int? _udpPort;
  Endpoint? _endpoint;

  UDP? _udp;

  bool _isReady = false;
  bool _isSending = false;

  // Camera
  final String esp32Ip = '192.168.4.100';
  late final WebViewController _cameraController;
  Timer? _captureTimer;

  String get streamUrl => 'http://$esp32Ip:81/stream';
  String get captureUrl => 'http://$esp32Ip/capture';

  @override
  void initState() {
    super.initState();

    _initCamera();
    _initUDP();

    WidgetsBinding.instance.addPostFrameCallback((_) {
      _loadSettings();
    });
  }

  // =========================
  // INIT
  // =========================
  void _initCamera() {
    _cameraController = WebViewController()..setJavaScriptMode(JavaScriptMode.unrestricted);
  }

  Future<void> _initUDP() async {
    final endpoint = Endpoint.any(port: Port(DEFAULT_UDP_PORT));
    _udp = await UDP.bind(endpoint);
    logger.d("UDP ready");
  }

  // =========================
  // SETTINGS SAFE LOAD
  // =========================
  Future<void> _loadSettings() async {
    final settings = context.read<SettingsProvider>();

    _receiverIp = settings.receiverIp;
    _udpPort = settings.udpPort;

    _endpoint = Endpoint.unicast(InternetAddress(_receiverIp!), port: Port(_udpPort!));

    _startCamera(settings.prefCaptureSpeed);

    setState(() {
      _isReady = true;
    });
  }

  // =========================
  // CAMERA MODE SWITCH
  // =========================
  void _startCamera(int speedMs) {
    _captureTimer?.cancel();

    if (speedMs < 300) {
      _startStream();
    } else {
      _startCapture(speedMs);
    }
  }

  void _startStream() {
    logger.d("Camera: STREAM");

    _cameraController.loadHtmlString('''
<html>
<body style="margin:0;background:black;">
<img src="$streamUrl"
     style="width:100%;height:100%;object-fit:cover;">
</body>
</html>
''');
  }

  void _startCapture(int interval) {
    logger.d("Camera: CAPTURE $interval ms");

    _captureTimer = Timer.periodic(Duration(milliseconds: interval), (_) async {
      try {
        final res = await http.get(Uri.parse(captureUrl));

        if (res.statusCode == 200) {
          final base64 = base64Encode(res.bodyBytes);

          _cameraController.loadHtmlString('''
<html>
<body style="margin:0;background:black;">
<img src="data:image/jpeg;base64,$base64"
     style="width:100%;height:100%;object-fit:cover;">
</body>
</html>
''');
        }
      } catch (e) {
        logger.w("Capture error: $e");
      }
    });
  }

  // =========================
  // UDP SAFE SEND
  // =========================
  Future<void> _send(String cmd) async {
    if (_isSending) return;
    if (_udp == null || _endpoint == null) return;

    _isSending = true;

    try {
      await _udp!.send(utf8.encode(cmd), _endpoint!);
    } finally {
      _isSending = false;
    }
  }

  @override
  void dispose() {
    _udp?.close();
    _captureTimer?.cancel();
    super.dispose();
  }

  // =========================
  // UI
  // =========================
  @override
  Widget build(BuildContext context) {
    final settings = context.watch<SettingsProvider>();

    return SafeArea(
      child: !_isReady
          ? const Center(child: CircularProgressIndicator())
          : SafeArea(
              child: CustomScrollView(
                slivers: [
                  const SliverToBoxAdapter(child: SizedBox(height: 10)),

                  // ================= JOYSTICK =================
                  SliverToBoxAdapter(child: SizedBox(height: 420, child: _joystick())),

                  // ================= CAMERA =================
                  SliverToBoxAdapter(
                    child: Container(
                      margin: const EdgeInsets.all(12),
                      height: 180,
                      decoration: BoxDecoration(
                        border: Border.all(color: Colors.grey),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      clipBehavior: Clip.hardEdge,
                      child: //WebViewWidget(controller: _cameraController),
                      Stack(
                        children: [
                          WebViewWidget(controller: _cameraController),

                          Positioned.fill(
                            child: GestureDetector(
                              onPanUpdate: _handleCameraDrag,
                              behavior: HitTestBehavior.translucent,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),

                  // ================= BUTTONS =================
                  SliverToBoxAdapter(
                    child: Padding(
                      padding: const EdgeInsets.all(16),
                      child: Wrap(
                        spacing: 10,
                        runSpacing: 10,
                        children: [
                          _btn('Hupen', 'HORN'),
                          _btn('Licht', 'LIGHT'),
                          _btn('Sirene', 'SIREN'),
                          _btn('Reset', 'RESET'),
                        ],
                      ),
                    ),
                  ),

                  SliverToBoxAdapter(
                    child: ElevatedButton(
                      onPressed: () => _send('TURN_IN_PLACE'),
                      child: const Text('Auf der Stelle wenden'),
                    ),
                  ),

                  SliverToBoxAdapter(
                    child: Padding(
                      padding: const EdgeInsets.all(20),
                      child: Text('IP=${settings.receiverIp}, Port=${settings.udpPort}'),
                    ),
                  ),
                ],
              ),
            ),
    );
  }

  // =========================
  // JOYSTICK WIDGET
  // =========================
  Widget _joystick() {
    return Center(
      child: LayoutBuilder(
        builder: (context, c) {
          final size = MediaQuery.of(context).size;
          final target = size.width * 0.5;
          const base = 120.0;

          return Transform.scale(
            scale: target / base,
            child: Joystick(
              mode: JoystickMode.all,
              listener: (d) {
                final x = d.x;
                final y = d.y;

                final p = math.sqrt(x * x + y * y);

                if (p < 0.1) {
                  _send('ms:0');
                  return;
                }

                final speed = (p * 100).toInt();

                if (y < -0.5) _send('mf:$speed');
                if (y > 0.5) _send('mb:$speed');
                if (x < -0.5) _send('ml:$speed');
                if (x > 0.5) _send('mr:$speed');
              },
            ),
          );
        },
      ),
    );
  }

  Widget _btn(String label, String cmd) {
    return ElevatedButton(onPressed: () => _send(cmd), child: Text(label));
  }

  void _handleCameraDrag(DragUpdateDetails details) {
    final dx = details.delta.dx;
    final dy = details.delta.dy;

    if (dx.abs() > 3) {
      if (dx > 0) {
        _send('cr');
      } else {
        _send('cl');
      }
    }

    if (dy.abs() > 3) {
      if (dy > 0) {
        _send('cd');
      } else {
        _send('cu');
      }
    }
  }
}
