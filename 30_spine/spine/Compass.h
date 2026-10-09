#pragma once

#include <Arduino.h>

// GY-273 (HMC5883L) magnetometer on I2C0, fixed address 0x1E (no jumper).
// Minimal register-level driver, no external library, matching the
// bare-metal style of PcfExpander/Motor. Soft-iron scaling is not
// implemented — hard-iron offsets are usually enough for a rough heading.
class Compass {
 public:
  explicit Compass(uint8_t address);

  // Starts I2C0 (100 kHz, shared with the PCF8574P) and configures the
  // HMC5883L (8-sample averaging, 15 Hz, continuous measurement).
  // Returns false if the chip doesn't ack.
  bool begin();

  // Reads one raw X/Y/Z sample and latches it for headingDeg().
  // Returns false on I2C error (latched values are left untouched).
  bool readRaw(int16_t& x, int16_t& y, int16_t& z);

  // Heading in degrees [0, 360) from the last successful readRaw(),
  // with the hard-iron offset and declination applied. NAN if the last
  // readRaw() failed.
  float headingDeg() const;

  // Hard-iron offsets in raw LSB, subtracted from X/Y before computing
  // the heading. Determined by calibration (see spine.ino 'c' command).
  void setOffsets(int16_t offsetX, int16_t offsetY) {
    offsetX_ = offsetX;
    offsetY_ = offsetY;
  }

  // Local magnetic declination in degrees (east positive), added to the
  // raw heading.
  void setDeclination(float declinationDeg) { declinationDeg_ = declinationDeg; }

  bool lastOk() const { return lastOk_; }

 private:
  uint8_t address_;
  int16_t offsetX_ = 0;
  int16_t offsetY_ = 0;
  float declinationDeg_ = 0.0f;
  int16_t lastX_ = 0, lastY_ = 0, lastZ_ = 0;
  bool lastOk_ = false;
};
