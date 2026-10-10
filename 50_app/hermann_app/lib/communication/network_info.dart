import '../global.dart';

class InfoNetwork {
  String ssid;
  String ip;
  String status;

  InfoNetwork({this.ssid = UNKNOWN_SSID, this.ip = UNKNOWN_IP, this.status = ''});
}
