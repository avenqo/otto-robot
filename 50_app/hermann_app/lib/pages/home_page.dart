import 'package:flutter/material.dart';

class VideoPage extends StatelessWidget {
  const VideoPage({super.key});

  @override
  Widget build(BuildContext context) {
    return const Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          Icon(Icons.videocam_off, size: 100, color: Colors.grey),
          SizedBox(height: 20),
          Text('Videostream (Dummy)', style: TextStyle(fontSize: 24, color: Colors.grey)),
          Text('Hier wird später der Livestream der ESP32-CAM angezeigt.', textAlign: TextAlign.center),
        ],
      ),
    );
  }
}
