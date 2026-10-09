#pragma once

#include <Arduino.h>

// PCF8574P on I2C0 (GP8/GP9), address 0x20. Quasi-bidirectional port: a pin
// written as 1 is an input (weak pull-up), written as 0 it drives low.
// Output bits are kept in a shadow byte so writing one output never clears
// the input pins (which must stay 1).
class PcfExpander {
 public:
  PcfExpander(uint8_t address, uint8_t inputMask);

  // Starts I2C0 at 100 kHz and writes the idle state (outputs low, inputs 1).
  bool begin();

  // Sets/clears one output bit in the shadow byte and writes it out.
  // Returns false on an I2C error (shadow keeps the requested value).
  bool writeBit(uint8_t bit, bool level);

  // Sets several output bits at once (single I2C transfer).
  bool writeBits(uint8_t mask, uint8_t values);

  // Re-sends the shadow byte (self-heals after a disturbed transfer).
  bool refresh();

  // Reads one input pin (last successful read wins on error, see lastOk()).
  bool readBit(uint8_t bit);

  bool lastOk() const { return lastOk_; }

 private:
  bool send();

  uint8_t address_;
  uint8_t inputMask_;
  uint8_t shadow_;
  uint8_t lastRead_ = 0xFF;
  bool lastOk_ = false;
};
