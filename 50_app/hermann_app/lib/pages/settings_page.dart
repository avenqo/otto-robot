import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../communication/network_info.dart';
import '../global.dart';
import '../settings/settings_provider.dart';

class SettingsPage extends StatelessWidget {
  const SettingsPage({super.key});

  @override
  Widget build(BuildContext context) {
    final settings = context.watch<SettingsProvider>();
    final ipController = TextEditingController(text: settings.receiverIp);
    final portController = TextEditingController(text: settings.udpPort.toString());
    final targetSSIDController = TextEditingController(text: settings.targetSSID);

    // Zeige SnackBar, wenn die SSID gewechselt hat
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (settings.currentSSID != UNKNOWN_SSID) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Aktuelle SSID: "${settings.currentSSID}"'), duration: const Duration(seconds: 2)),
        );
      }
      // Prüfe, ob die aktuelle SSID der Soll-SSID entspricht
      if (settings.targetSSID.isNotEmpty && settings.currentSSID != settings.targetSSID) {
        settings.promptToConnectToTargetSSID(context);
      }
    });

    return Padding(
      padding: const EdgeInsets.all(16.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Aktuelle SSID anzeigen
          Text(
            'Aktuelle SSID: ${settings.currentSSID}',
            style: TextStyle(
              fontSize: 18,
              color: settings.currentSSID == settings.targetSSID ? Colors.green : Colors.red,
            ),
          ),
          const SizedBox(height: 5),
          // Soll-SSID anzeigen (falls gesetzt)
          if (settings.targetSSID.isNotEmpty)
            Text('Soll-SSID: ${settings.targetSSID}', style: const TextStyle(fontSize: 16)),
          const SizedBox(height: 20),
          // Textfeld für Soll-SSID
          TextField(
            controller: targetSSIDController,
            decoration: const InputDecoration(
              labelText: 'Soll-SSID (optional)',
              border: OutlineInputBorder(),
              hintText: 'z. B. Hermann_AP',
            ),
          ),
          const SizedBox(height: 10),
          // Textfelder für IP und Port
          TextField(
            controller: ipController,
            decoration: const InputDecoration(labelText: 'Empfänger-IP', border: OutlineInputBorder()),
          ),
          const SizedBox(height: 10),
          TextField(
            controller: portController,
            decoration: const InputDecoration(labelText: 'UDP-Port', border: OutlineInputBorder()),
            keyboardType: TextInputType.number,
          ),
          const SizedBox(height: 20),
          // Button zum Speichern
          ElevatedButton(
            onPressed: () {
              settings.saveSettings(
                ipController.text,
                int.tryParse(portController.text) ?? DEFAULT_UDP_PORT,
                targetSSIDController.text,
              );
              ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Einstellungen gespeichert')));
            },
            child: const Text('Speichern'),
          ),
          const SizedBox(height: 20),

          // --- NEU: Aktuelle IP anzeigen ---
          FutureBuilder<InfoNetwork>(
            future: settings.getCurrentInfoNetwork(), // Ruft die Methode auf
            builder: (context, snapshot) {
              if (snapshot.connectionState == ConnectionState.waiting) {
                return const Text('IP wird geladen...');
              } else if (snapshot.hasError) {
                return Text('Fehler beim Laden der IP: ${snapshot.error}');
              } else {
                final ip = snapshot.data?.ip ?? 'Unbekannt';
                return Text('Aktuelle IP: $ip', style: const TextStyle(fontSize: 16));
              }
            },
          ),
          const SizedBox(height: 10),

          // Hinweis, wenn die aktuelle SSID nicht der Soll-SSID entspricht
          if (settings.targetSSID.isNotEmpty && settings.currentSSID != settings.targetSSID)
            Card(
              color: Colors.amber[100],
              child: Padding(
                padding: const EdgeInsets.all(8.0),
                child: Text(
                  'Hinweis: Die aktuelle SSID "${settings.currentSSID}" stimmt nicht mit der Soll-SSID "${settings.targetSSID}" überein. Bitte verbinde dich mit "${settings.targetSSID}".',
                  style: const TextStyle(color: Colors.black87),
                ),
              ),
            ),
        ],
      ),
    );
  }
}
