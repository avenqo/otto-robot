#pragma once

#include <Arduino.h>

#include "PcfExpander.h"

// One channel of an L298N driver: PWM enable on a native RP2040 pin, the two
// direction inputs on PCF8574P ports (see Config.h). Stopping only needs the
// enable pin, so an I2C fault can never keep a motor running.
class Motor {
 public:
  Motor(int pinEnable, PcfExpander& pcf, uint8_t bitIn1, uint8_t bitIn2);

  void begin();

  // speedMmS: signed target speed in mm/s, clamped to +-MAX_SPEED_MM_S.
  // If the direction has to change, EN is dropped first, then the direction
  // is written (one I2C transfer), then PWM resumes. If the I2C write fails
  // the motor stays stopped.
  void setSpeed(float speedMmS);

  // Enable pin low (coast). Native pin only, no I2C.
  void stop();

 private:
  int pinEnable_;
  PcfExpander& pcf_;
  uint8_t bitIn1_;
  uint8_t bitIn2_;
  int8_t dir_ = 0;  // 0 = unknown/stopped, +1 = forward, -1 = backward
};
