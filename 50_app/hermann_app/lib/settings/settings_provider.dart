import 'dart:async';
import 'package:flutter/material.dart';
import 'package:permission_handler/permission_handler.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:network_info_plus/network_info_plus.dart';

import '../communication/network_info.dart';
import '../global.dart';

class SettingsProvider with ChangeNotifier {
  String _receiverIp = ROBOT_IP;
  int _udpPort = DEFAULT_UDP_PORT;
  String _currentSSID = UNKNOWN_SSID;
  int _captureSpeed = 1000; // ms for camera capture, could also be made configurable
  String _targetSSID = SSID; // Soll-SSID
  bool _isCheckingSSID = false;
  Timer? _ssidCheckTimer;

  // Getter
  String get receiverIp => _receiverIp;
  int get udpPort => _udpPort;
  String get currentSSID => _currentSSID;
  String get targetSSID => _targetSSID;
  int get prefCaptureSpeed => _captureSpeed; // Beispielwert, könnte auch aus SharedPreferences geladen werden

  SettingsProvider() {
    _startSSIDCheckTimer();
  }

  @override
  void dispose() {
    _ssidCheckTimer?.cancel();
    super.dispose();
  }

  // Startet den Timer für die SSID-Prüfung
  void _startSSIDCheckTimer() {
    _ssidCheckTimer = Timer.periodic(const Duration(seconds: 5), (timer) async {
      await _checkAndUpdateSSID();
    });
  }

  // Prüft und aktualisiert die SSID
  Future<void> _checkAndUpdateSSID() async {
    if (_isCheckingSSID) return;
    _isCheckingSSID = true;
    try {
      final infoNetwork = await getCurrentInfoNetwork();
      if (infoNetwork.ssid != _currentSSID) {
        _currentSSID = infoNetwork.ssid;

        notifyListeners(); // UI aktualisieren
      }
    } catch (e) {
      debugPrint('Fehler beim Abrufen der SSID: $e');
      _currentSSID = 'Fehler: $e';
      notifyListeners();
    } finally {
      _isCheckingSSID = false;
    }
  }

  Future<InfoNetwork> getCurrentInfoNetwork() async {
    try {
      // Berechtigungen anfragen
      final permissionStatus = await Permission.locationWhenInUse.request();
      if (!permissionStatus.isGranted) {
        return InfoNetwork(ssid: 'Berechtigung verweigert', ip: UNKNOWN_IP, status: 'error: permission_denied');
      }

      final info = NetworkInfo();
      /*
      final gip = await info.getWifiGatewayIP();
      final k = await info.getWifiBSSID();
      final p = await info.getWifiBroadcast();
      final t = await info.getWifiIP();
      final r = info.toString();
      */

      // SSID abrufen und Anführungszeichen entfernen
      final ssid = await info.getWifiName();
      final cleanedSSID = ssid?.replaceAll('"', '') ?? UNKNOWN_SSID;

      // IP abrufen
      final ip = await info.getWifiIP() ?? UNKNOWN_IP;

      return InfoNetwork(ssid: cleanedSSID, ip: ip, status: 'success');
    } catch (e) {
      return InfoNetwork(ssid: UNKNOWN_SSID, ip: UNKNOWN_IP, status: 'error: $e');
    }
  }

  // Lädt die Einstellungen aus SharedPreferences
  Future<void> loadSettings() async {
    final prefs = await SharedPreferences.getInstance();
    _receiverIp = prefs.getString('receiverIp') ?? '192.168.4.1';
    _udpPort = prefs.getInt('udpPort') ?? DEFAULT_UDP_PORT;
    _targetSSID = prefs.getString('targetSSID') ?? 'HermannFunkt';
    await _checkAndUpdateSSID(); // Sofortige SSID-Prüfung
    notifyListeners();
  }

  // Speichert die Einstellungen
  Future<void> saveSettings(String ip, int port, String targetSSID) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString('receiverIp', ip);
    await prefs.setInt('udpPort', port);
    await prefs.setString('targetSSID', targetSSID);
    _receiverIp = ip;
    _udpPort = port;
    _targetSSID = targetSSID;
    notifyListeners();
  }

  // Zeigt eine SnackBar, wenn die SSID nicht der Soll-SSID entspricht
  void promptToConnectToTargetSSID(BuildContext context) {
    if (_targetSSID.isEmpty || _currentSSID == _targetSSID || _currentSSID == UNKNOWN_SSID) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('Aktuelle SSID: "$_currentSSID". Bitte verbinde dich mit "$_targetSSID".'),
        action: SnackBarAction(label: 'OK', onPressed: () {}),
      ),
    );
  }
}
