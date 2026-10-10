import 'dart:io';

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:path_provider/path_provider.dart';
import 'package:webview_flutter/webview_flutter.dart';

class VideoPage extends StatefulWidget {
  const VideoPage({super.key});

  @override
  State<VideoPage> createState() => _VideoPageState();
}

class _VideoPageState extends State<VideoPage> {
  // ESP32-CAM IP
  final String esp32Ip = '192.168.4.100';

  late final WebViewController _controller;

  bool _isLoading = true;
  bool _hasError = false;

  String get streamUrl => 'http://$esp32Ip:81/stream';

  String get captureUrl => 'http://$esp32Ip/capture';

  @override
  void initState() {
    super.initState();

    _controller = WebViewController()..setJavaScriptMode(JavaScriptMode.unrestricted);
    /*
    _controller = WebViewController()
      ..setJavaScriptMode(JavaScriptMode.unrestricted)
      ..setNavigationDelegate(
        NavigationDelegate(
          onPageStarted: (_) {
            setState(() {
              _isLoading = true;
              _hasError = false;
            });
          },

          onPageFinished: (_) {
            setState(() {
              _isLoading = false;
            });
          },

          onWebResourceError: (error) {
            setState(() {
              _isLoading = false;
              _hasError = true;
            });
          },
        ),
      );*/

    _loadStream();
  }

  Future<void> _loadStream() async {
    setState(() {
      _isLoading = true;
      _hasError = false;
    });

    try {
      final response = await http.get(Uri.parse(captureUrl)).timeout(const Duration(seconds: 5));

      if (response.statusCode != 200) {
        throw Exception('Kamera nicht erreichbar');
      }

      final html =
          '''
<!DOCTYPE html>
<html>
<head>
<meta name="viewport"
      content="width=device-width,
               initial-scale=1.0,
               maximum-scale=5.0,
               user-scalable=yes">
<style>
html, body {
  margin: 0;
  padding: 0;
  background: black;
  overflow: hidden;
  width: 100%;
  height: 100%;
}

img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}
</style>
</head>
<body>
  <img src="$streamUrl">
</body>
</html>
''';

      await _controller.loadHtmlString(html);

      setState(() {
        _isLoading = false;
        _hasError = false;
      });
    } catch (e) {
      setState(() {
        _isLoading = false;
        _hasError = true;
      });
    }
  }

  // TODO: delete
  Future<void> _loadStream_old() async {
    setState(() {
      _isLoading = true;
      _hasError = false;
    });

    try {
      // Verbindung testen
      final response = await http.get(Uri.parse(captureUrl)).timeout(const Duration(seconds: 5));

      if (response.statusCode == 200) {
        await _controller.loadRequest(Uri.parse(streamUrl));

        setState(() {
          _hasError = false;
        });
      } else {
        setState(() {
          _hasError = true;
        });
      }
    } catch (e) {
      setState(() {
        _hasError = true;
      });
    } finally {
      setState(() {
        _isLoading = false;
      });
    }
  }

  Future<void> _takePhoto() async {
    try {
      ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Foto wird aufgenommen...')));

      final response = await http.get(Uri.parse(captureUrl)).timeout(const Duration(seconds: 10));

      if (response.statusCode != 200) {
        throw Exception('Kamera antwortet nicht');
      }

      final directory = await getExternalStorageDirectory();

      if (directory == null) {
        throw Exception('Kein Speicher verfügbar');
      }

      final timestamp = DateTime.now().millisecondsSinceEpoch;

      final file = File('${directory.path}/esp32cam_$timestamp.jpg');

      await file.writeAsBytes(response.bodyBytes);

      if (!mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Foto gespeichert:\n${file.path}')));
    } catch (e) {
      if (!mounted) return;

      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Fehler beim Fotografieren:\n$e')));
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Camera Stream'),

        actions: [
          // Stream neu laden
          IconButton(
            icon: const Icon(Icons.refresh),

            onPressed: () async {
              await _loadStream();
            },
          ),

          // Foto aufnehmen
          IconButton(
            icon: const Icon(Icons.camera_alt),

            onPressed: () async {
              await _takePhoto();
            },
          ),
        ],
      ),

      body: Stack(
        children: [
          if (!_hasError) WebViewWidget(controller: _controller),

          if (_isLoading) const Center(child: CircularProgressIndicator()),

          if (_hasError)
            Center(
              child: Padding(
                padding: const EdgeInsets.all(24),

                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,

                  children: [
                    const Icon(Icons.wifi_off, size: 100, color: Colors.red),

                    const SizedBox(height: 20),

                    const Text(
                      'ESP32-CAM nicht erreichbar',
                      style: TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
                      textAlign: TextAlign.center,
                    ),

                    const SizedBox(height: 10),

                    Text(esp32Ip, style: const TextStyle(fontSize: 18, color: Colors.grey)),

                    const SizedBox(height: 30),

                    ElevatedButton.icon(
                      onPressed: () async {
                        await _loadStream();
                      },

                      icon: const Icon(Icons.refresh),

                      label: const Text('Erneut versuchen'),
                    ),
                  ],
                ),
              ),
            ),
        ],
      ),
    );
  }
}
