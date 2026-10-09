#include "Motor.h"

#include "Config.h"

Motor::Motor(int pinEnable, PcfExpander& pcf, uint8_t bitIn1, uint8_t bitIn2)
    : pinEnable_(pinEnable), pcf_(pcf), bitIn1_(bitIn1), bitIn2_(bitIn2) {}

void Motor::begin() {
  pinMode(pinEnable_, OUTPUT);
  stop();
}

void Motor::setSpeed(float speedMmS) {
  speedMmS = constrain(speedMmS, -MAX_SPEED_MM_S, MAX_SPEED_MM_S);

  int8_t wanted = speedMmS >= 0 ? 1 : -1;
  if (wanted != dir_) {
    analogWrite(pinEnable_, 0);  // bridge off while the direction changes
    uint8_t mask = (1u << bitIn1_) | (1u << bitIn2_);
    uint8_t values = wanted > 0 ? (1u << bitIn1_) : (1u << bitIn2_);
    if (!pcf_.writeBits(mask, values)) {
      dir_ = 0;  // unknown state: stay stopped, retry on the next command
      return;
    }
    dir_ = wanted;
  }

  int pwm = static_cast<int>((fabsf(speedMmS) / MAX_SPEED_MM_S) * PWM_MAX);
  analogWrite(pinEnable_, constrain(pwm, 0, PWM_MAX));
}

void Motor::stop() {
  analogWrite(pinEnable_, 0);
}
