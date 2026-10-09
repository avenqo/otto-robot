// Otto "spine" — RP2040 core: drive commands from the Jetson over USB
// serial, differential-drive motor control, and a command watchdog.
//
// Protocol (see README.md):
//   Jetson -> RP2040:  V,<linear_mm_s>,<angular_mrad_s>\n
//   RP2040 -> Jetson:  T,<heading_deg>,<lat>,<lon>,<gps_fix>,<radar>,<batt_mV>\n
//
// Manual test commands (type into the Arduino Serial Monitor, Newline
// line ending, 115200 baud) — see printHelp() below for the full list.
// Any recognized drive command (V, M, or w/a/s/d) re-arms the watchdog;
// like the Jetson link, motors stop if no drive command follows within
// DRIVE_COMMAND_TIMEOUT_MS, so keep resending while testing continuously.
//
// Sensors (GPS, radar, battery) are not wired up yet; telemetry reports
// placeholder zeros for those. Each remaining TODO marks where a sensor
// module will plug in. The GY-273 compass is wired up (see Compass.h).

#include "Compass.h"
#include "Config.h"
#include "Motor.h"
#include "PcfExpander.h"

PcfExpander pcf(PCF8574_ADDR, PCF_INPUT_MASK);
Motor motorLeft(OTTO_PIN_MOTOR_L_EN, pcf, PCF_PORT_MOTOR_L_IN1, PCF_PORT_MOTOR_L_IN2);
Motor motorRight(OTTO_PIN_MOTOR_R_EN, pcf, PCF_PORT_MOTOR_R_IN1, PCF_PORT_MOTOR_R_IN2);
Compass compass(COMPASS_ADDR);
unsigned long lastPcfRefreshMs = 0;

unsigned long lastCommandMs = 0;
unsigned long lastTelemetryMs = 0;
bool telemetryEnabled = true;

// Streams raw X/Y/Z + heading at a fast, fixed rate instead of normal
// telemetry — for bring-up and hard-iron calibration (rotate Otto by
// hand while watching min/max X/Y in the Serial Monitor).
bool compassTestMode = false;
unsigned long lastCompassTestMs = 0;
constexpr unsigned long COMPASS_TEST_INTERVAL_MS = 100;

char lineBuf[64];
uint8_t lineLen = 0;

void applyDrive(float linearMmS, float angularMradS) {
  float omegaRadS = angularMradS / 1000.0f;
  float halfTrack = TRACK_WIDTH_MM / 2.0f;

  motorLeft.setSpeed(linearMmS - omegaRadS * halfTrack);
  motorRight.setSpeed(linearMmS + omegaRadS * halfTrack);
}

void applyRaw(float leftMmS, float rightMmS) {
  motorLeft.setSpeed(leftMmS);
  motorRight.setSpeed(rightMmS);
}

void stopMotors() {
  motorLeft.stop();
  motorRight.stop();
}

void printHelp() {
  Serial.println(F("Otto spine — manual test commands:"));
  Serial.println(F("  V,<linear_mm_s>,<angular_mrad_s>  drive kinematics (Jetson protocol)"));
  Serial.println(F("  M,<left_mm_s>,<right_mm_s>        raw per-wheel speed, e.g. to test one motor"));
  Serial.println(F("  w / s                              forward / backward, fixed test speed"));
  Serial.println(F("  a / d                              pivot left / right, fixed test speed"));
  Serial.println(F("  x                                  stop"));
  Serial.println(F("  q                                  toggle telemetry printing on/off"));
  Serial.println(F("  c                                  toggle compass test/calibration mode"));
  Serial.println(F("  ?                                  show this help"));
  Serial.print(F("Note: motors stop automatically "));
  Serial.print(DRIVE_COMMAND_TIMEOUT_MS);
  Serial.println(F("ms after the last drive command — resend to keep driving."));
  Serial.println(pcf.refresh() ? F("PCF8574P (0x20): ok")
                               : F("WARNING: PCF8574P (0x20) not responding"));
}

void printCompassRaw() {
  int16_t x, y, z;
  if (!compass.readRaw(x, y, z)) {
    Serial.println(F("compass: read failed"));
    return;
  }
  Serial.printf("compass raw X=%d Y=%d Z=%d heading=%.1f\n", x, y, z,
                compass.headingDeg());
}

void handleLine(const char* line) {
  float a, b;

  if (line[0] == 'V' && sscanf(line, "V,%f,%f", &a, &b) == 2) {
    applyDrive(a, b);
    lastCommandMs = millis();
  } else if (line[0] == 'M' && sscanf(line, "M,%f,%f", &a, &b) == 2) {
    applyRaw(a, b);
    lastCommandMs = millis();
  } else if (line[0] == 'w' && line[1] == '\0') {
    applyRaw(TEST_SPEED_MM_S, TEST_SPEED_MM_S);
    lastCommandMs = millis();
  } else if (line[0] == 's' && line[1] == '\0') {
    applyRaw(-TEST_SPEED_MM_S, -TEST_SPEED_MM_S);
    lastCommandMs = millis();
  } else if (line[0] == 'a' && line[1] == '\0') {
    applyRaw(-TEST_SPEED_MM_S, TEST_SPEED_MM_S);
    lastCommandMs = millis();
  } else if (line[0] == 'd' && line[1] == '\0') {
    applyRaw(TEST_SPEED_MM_S, -TEST_SPEED_MM_S);
    lastCommandMs = millis();
  } else if (line[0] == 'x' && line[1] == '\0') {
    stopMotors();
    lastCommandMs = millis();
  } else if (line[0] == 'q' && line[1] == '\0') {
    telemetryEnabled = !telemetryEnabled;
    Serial.print(F("telemetry "));
    Serial.println(telemetryEnabled ? F("on") : F("off"));
  } else if (line[0] == 'c' && line[1] == '\0') {
    compassTestMode = !compassTestMode;
    Serial.print(F("compass test mode "));
    Serial.println(compassTestMode ? F("on") : F("off"));
  } else if (line[0] == '?' && line[1] == '\0') {
    printHelp();
  } else if (line[0] != '\0') {
    Serial.print(F("unrecognized command: "));
    Serial.println(line);
  }
}

void readSerial() {
  while (Serial.available() > 0) {
    char c = Serial.read();
    if (c == '\n') {
      lineBuf[lineLen] = '\0';
      handleLine(lineBuf);
      lineLen = 0;
    } else if (c != '\r' && lineLen < sizeof(lineBuf) - 1) {
      lineBuf[lineLen++] = c;
    } else if (lineLen >= sizeof(lineBuf) - 1) {
      // Line too long / garbage — drop it and resync on the next '\n'.
      lineLen = 0;
    }
  }
}

void sendTelemetry() {
  int16_t cx, cy, cz;
  compass.readRaw(cx, cy, cz);
  float headingDeg = compass.headingDeg();  // NAN if the read above failed
  // TODO: lat/lon/fix from GPS Neo-6M module
  float lat = 0.0f, lon = 0.0f;
  int gpsFix = 0;
  // TODO: presence flag from HLK-LD2402 radar module
  int radar = 0;
  // TODO: battery voltage via ADC
  int battMv = 0;

  Serial.printf("T,%.1f,%.6f,%.6f,%d,%d,%d\n", headingDeg, lat, lon, gpsFix,
                radar, battMv);
}

void setup() {
  Serial.begin(SERIAL_BAUD);

  bool pcfOk = pcf.begin();
  motorLeft.begin();
  motorRight.begin();

  bool compassOk = compass.begin();
  compass.setOffsets(COMPASS_OFFSET_X, COMPASS_OFFSET_Y);
  compass.setDeclination(COMPASS_DECLINATION_DEG);

  // USB-CDC output is lost until a host has the port open — wait briefly so
  // the messages below are visible when the Serial Monitor is already open.
  unsigned long waitStart = millis();
  while (!Serial && millis() - waitStart < 3000) {
    delay(10);
  }

  Serial.println(F("=== Here is OTTO ==="));
  if (!pcfOk) {
    Serial.println(F("WARNING: PCF8574P (0x20) not responding — motor direction unavailable"));
  }
  if (!compassOk) {
    Serial.println(F("WARNING: GY-273 compass (0x1E) not responding — heading unavailable"));
  }

  lastCommandMs = millis();

  printHelp();

  Serial.println(F("=== OTTO: Setup done ==="));
}

void loop() {
  readSerial();

  if (millis() - lastCommandMs > DRIVE_COMMAND_TIMEOUT_MS) {
    stopMotors();
  }

  if (millis() - lastPcfRefreshMs >= PCF_REFRESH_MS) {
    pcf.refresh();
    lastPcfRefreshMs = millis();
  }

  if (telemetryEnabled && millis() - lastTelemetryMs >= TELEMETRY_INTERVAL_MS) {
    sendTelemetry();
    lastTelemetryMs = millis();
  }

  if (compassTestMode && millis() - lastCompassTestMs >= COMPASS_TEST_INTERVAL_MS) {
    printCompassRaw();
    lastCompassTestMs = millis();
  }
}
