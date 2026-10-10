// I2C scanner for the Otto spine bring-up (RP2040, arduino-pico).
//
// Uses the spine's real pins (GP8 = SDA, GP9 = SCL, I2C0) — Wire's defaults
// on the Pico are GP4/GP5, which is NOT where Otto's bus is wired.
// Expected devices: PCF8574P at 0x20, GY-273 at 0x1E (HMC5883L) or 0x2C (QMC5883P).
// For every device the first register is printed: a QMC5883P reads 0x80.
//
// Serial Monitor: 115200 baud.

#include <Wire.h>

constexpr int PIN_SDA = 8;
constexpr int PIN_SCL = 9;

void setup() {
  Serial.begin(115200);
  while (!Serial && millis() < 5000) {
    delay(10);
  }

  // Idle levels before the I2C peripheral takes over the pins: with a
  // module that has pull-ups (GY-273, most PCF8574 breakouts) both lines
  // read 1. A 0 means: short to GND, no pull-up, or the module is unpowered.
  pinMode(PIN_SDA, INPUT);
  pinMode(PIN_SCL, INPUT);
  delay(5);
  Serial.printf("Idle levels: SDA(GP%d)=%d SCL(GP%d)=%d (expect 1/1 with pull-ups)\n",
                PIN_SDA, digitalRead(PIN_SDA), PIN_SCL, digitalRead(PIN_SCL));

  Wire.setSDA(PIN_SDA);
  Wire.setSCL(PIN_SCL);
  Wire.begin();
  Wire.setClock(100000);
  Wire.setTimeout(25, true);
  Serial.println("I2C scanner ready.");
}

void loop() {
  int found = 0;
  Serial.println("Scanning 0x01..0x7E ...");
  for (uint8_t address = 1; address < 127; address++) {
    Wire.beginTransmission(address);
    uint8_t error = Wire.endTransmission();
    if (error == 0) {
      Wire.beginTransmission(address);
      Wire.write(0x00);
      int reg0 = -1;
      if (Wire.endTransmission(false) == 0 && Wire.requestFrom(static_cast<int>(address), 1) == 1) {
        reg0 = Wire.read();
      }
      Serial.printf("  device at 0x%02X (reg 0x00 = 0x%02X)\n", address, reg0 & 0xFF);
      found++;
    } else if (error != 2 && error != 3) {  // 2/3 = plain NACK, expected for empty addresses
      Serial.printf("  0x%02X: bus error %u\n", address, error);
    }
  }
  if (found == 0) {
    Serial.println("No devices found.");
  } else {
    Serial.printf("%d device(s) found.\n", found);
  }
  Serial.println();
  delay(3000);
}
