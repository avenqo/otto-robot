#include "PcfExpander.h"

#include <Wire.h>

#include "Config.h"

PcfExpander::PcfExpander(uint8_t address, uint8_t inputMask)
    : address_(address), inputMask_(inputMask), shadow_(inputMask) {}

bool PcfExpander::begin() {
  Wire.setSDA(OTTO_PIN_I2C0_SDA);
  Wire.setSCL(OTTO_PIN_I2C0_SCL);
  Wire.begin();
  Wire.setClock(100000);  // PCF8574 is specified for 100 kHz
  Wire.setTimeout(I2C_TIMEOUT_MS, true);  // never block loop() on a stuck bus
  shadow_ = inputMask_;   // all outputs low, inputs (and unused) high
  return send();
}

bool PcfExpander::send() {
  Wire.beginTransmission(address_);
  Wire.write(shadow_);
  lastOk_ = (Wire.endTransmission() == 0);
  return lastOk_;
}

bool PcfExpander::writeBit(uint8_t bit, bool level) {
  return writeBits(1u << bit, level ? 0xFF : 0x00);
}

bool PcfExpander::writeBits(uint8_t mask, uint8_t values) {
  mask &= ~inputMask_;  // never touch input pins
  shadow_ = (shadow_ & ~mask) | (values & mask);
  return send();
}

bool PcfExpander::refresh() { return send(); }

bool PcfExpander::readBit(uint8_t bit) {
  if (Wire.requestFrom(static_cast<int>(address_), 1) == 1) {
    lastRead_ = Wire.read();
    lastOk_ = true;
  } else {
    lastOk_ = false;
  }
  return (lastRead_ >> bit) & 1u;
}
