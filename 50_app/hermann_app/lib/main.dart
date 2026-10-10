import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'global.dart';
import 'pages/settings_page.dart';
import 'pages/control_page.dart';
import 'pages/video_page.dart';
import 'settings/settings_provider.dart';

void main() {
  runApp(const HermannApp());
}

class HermannApp extends StatelessWidget {
  const HermannApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [ChangeNotifierProvider(create: (_) => SettingsProvider())],
      child: MaterialApp(
        title: APP_TITLE,
        theme: ThemeData(primarySwatch: Colors.blue, useMaterial3: true),
        home: const HomePage(),
      ),
    );
  }
}

class HomePage extends StatefulWidget {
  const HomePage({super.key});

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  int _currentIndex = 0;

  @override
  void initState() {
    super.initState();
    // Lade Einstellungen und SSID beim Start
    context.read<SettingsProvider>().loadSettings();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text(APP_TITLE)),
      body: IndexedStack(index: _currentIndex, children: const [ControlPage(), SettingsPage(), VideoPage()]),
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: _currentIndex,
        onTap: (index) => setState(() => _currentIndex = index),
        items: const [
          BottomNavigationBarItem(icon: Icon(Icons.gamepad), label: 'Steuerung'),
          BottomNavigationBarItem(icon: Icon(Icons.settings), label: 'Einstellungen'),
          BottomNavigationBarItem(icon: Icon(Icons.videocam), label: 'Video'),
        ],
      ),
    );
  }
}
