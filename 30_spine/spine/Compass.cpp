#include "Compass.h"

#include <Wire.h>

#include "Config.h"

namespace {
constexpr uint8_t REG_CONFIG_A = 0x00;
constexpr uint8_t REG_CONFIG_B = 0x01;
constexpr uint8_t REG_MODE = 0x02;
constexpr uint8_t REG_DATA_X_MSB = 0x03;

constexpr uint8_t CONFIG_A_8AVG_15HZ = 0b01110000;  // 8-sample avg, 15 Hz, normal measurement
constexpr uint8_t CONFIG_B_GAIN_1_3GA = 0b00100000;  // +-1.3 Ga, default gain
constexpr uint8_t MODE_CONTINUOUS = 0x00;
}  // namespace

Compass::Compass(uint8_t address) : address_(address) {}

bool Compass::begin() {
  Wire.setSDA(OTTO_PIN_I2C0_SDA);
  Wire.setSCL(OTTO_PIN_I2C0_SCL);
  Wire.begin();
  Wire.setClock(100000);
  Wire.setTimeout(I2C_TIMEOUT_MS, true);  // never block loop() on a stuck bus

  Wire.beginTransmission(address_);
  Wire.write(REG_CONFIG_A);
  Wire.write(CONFIG_A_8AVG_15HZ);
  Wire.write(CONFIG_B_GAIN_1_3GA);
  Wire.write(MODE_CONTINUOUS);
  lastOk_ = (Wire.endTransmission() == 0);
  return lastOk_;
}

bool Compass::readRaw(int16_t& x, int16_t& y, int16_t& z) {
  Wire.beginTransmission(address_);
  Wire.write(REG_DATA_X_MSB);
  if (Wire.endTransmission(false) != 0) {
    lastOk_ = false;
    return false;
  }

  if (Wire.requestFrom(static_cast<int>(address_), 6) != 6) {
    lastOk_ = false;
    return false;
  }

  // HMC5883L data register order is X, Z, Y (not X, Y, Z).
  x = static_cast<int16_t>((Wire.read() << 8) | Wire.read());
  z = static_cast<int16_t>((Wire.read() << 8) | Wire.read());
  y = static_cast<int16_t>((Wire.read() << 8) | Wire.read());

  lastX_ = x;
  lastY_ = y;
  lastZ_ = z;
  lastOk_ = true;
  return true;
}

float Compass::headingDeg() const {
  if (!lastOk_) return NAN;

  float x = lastX_ - offsetX_;
  float y = lastY_ - offsetY_;

  float heading = atan2(y, x) * 180.0f / PI;
  heading += declinationDeg_;
  if (heading < 0.0f) heading += 360.0f;
  if (heading >= 360.0f) heading -= 360.0f;
  return heading;
}
