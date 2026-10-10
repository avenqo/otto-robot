import 'package:flutter/material.dart';
import 'package:network_info_plus/network_info_plus.dart';
// TODO: unbenutzt?

class SSIDChecker extends StatefulWidget {
  const SSIDChecker({super.key});

  @override
  State<SSIDChecker> createState() => _SSIDCheckerState();
}

class _SSIDCheckerState extends State<SSIDChecker> {
  String _currentSSID = 'Unbekannt';

  @override
  void initState() {
    super.initState();
    _getCurrentSSID();
  }

  Future<void> _getCurrentSSID() async {
    try {
      final info = NetworkInfo();
      final ssid = await info.getWifiName();
      setState(() {
        _currentSSID = ssid ?? 'Unbekannt';
      });
    } catch (e) {
      setState(() {
        _currentSSID = 'Fehler: $e';
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Aktuelle SSID')),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text('Aktuelle SSID:', style: Theme.of(context).textTheme.headlineSmall),
            const SizedBox(height: 10),
            Text(_currentSSID, style: Theme.of(context).textTheme.bodyLarge),
            const SizedBox(height: 20),
            ElevatedButton(onPressed: _getCurrentSSID, child: const Text('SSID neu laden')),
          ],
        ),
      ),
    );
  }
}
