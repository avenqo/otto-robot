#pragma once

// Pin assignment per 10_concepts/otto-concept.md.
// Jetson link uses native USB (Serial/USB-CDC), not UART0 — GP0/GP1 are
// therefore free for other uses (GP0 = DFPlayer RX, GP1 = head servo).

// Motors: one L298N board per motor, both internal H-bridges jumpered in
// parallel on the board (ENA+ENB, IN1+IN4, IN2+IN3) for ~3-4A per motor.
// PWM enable stays on native RP2040 pins; the direction inputs (IN1/IN2)
// sit on the PCF8574P (I2C, see below). Stopping only needs EN low.
// See 20_hardware/motor-wiring.md for the full jumpering/power diagram.
constexpr int OTTO_PIN_MOTOR_L_EN = 2;   // PWM -> board #1 ENA+ENB
constexpr int OTTO_PIN_MOTOR_R_EN = 5;   // PWM -> board #2 ENA+ENB
// (GP3, GP4, GP6, GP7 are now free — direction moved to the PCF8574P.)

// I2C0: GY-273 compass (on the deck, away from motors), 1x PCF8574P
// expander (0x20, default address, no jumper needed). Color sensors (TCS3200/TCS34725) dropped from the
// design. WT588D (parallel/key-trigger sound module) replaced by a
// DFPlayer Mini (UART-controlled, see below) — the PCF8574 no longer
// carries audio trigger lines. It now handles the L298N direction outputs
// (P2-P5), the vibration sensor and the DFPlayer BUSY input (P0/P1).
constexpr int OTTO_PIN_I2C0_SDA = 8;
constexpr int OTTO_PIN_I2C0_SCL = 9;
constexpr uint8_t PCF8574_ADDR = 0x20;
// GY-273 boards come with two different chips: HMC5883L at 0x1E, or the newer
// QMC5883P at 0x2C (register map differs; Compass picks the driver by address).
// Otto's board shows up at 0x2C (I2C scan) -> QMC5883P.
constexpr uint8_t COMPASS_ADDR = 0x2C;
constexpr uint8_t PCF_PORT_VIBRATION = 0;       // P0: SW-420 DO (input)
constexpr uint8_t PCF_PORT_DFPLAYER_BUSY = 1;   // P1: active-low while playing (input)
constexpr uint8_t PCF_PORT_MOTOR_L_IN1 = 2;     // P2 -> board #1 IN1+IN4
constexpr uint8_t PCF_PORT_MOTOR_L_IN2 = 3;     // P3 -> board #1 IN2+IN3
constexpr uint8_t PCF_PORT_MOTOR_R_IN1 = 4;     // P4 -> board #2 IN1+IN4
constexpr uint8_t PCF_PORT_MOTOR_R_IN2 = 5;     // P5 -> board #2 IN2+IN3
// Pins that must stay 1 (inputs + unused P6/P7): P0, P1, P6, P7
constexpr uint8_t PCF_INPUT_MASK = 0b11000011;
// Direction bits are re-sent this often so a disturbed transfer self-heals.
constexpr unsigned long PCF_REFRESH_MS = 20;

// Compass hard-iron offsets (raw LSB), subtracted from X/Y before the
// heading is computed — motors/PCF8574/servo nearby distort the raw
// field. Both 0 until calibrated on the assembled robot (see spine.ino
// 'c' command, which streams raw X/Y/Z while you rotate Otto by hand).
constexpr int16_t COMPASS_OFFSET_X = 0;
constexpr int16_t COMPASS_OFFSET_Y = 0;
// Local magnetic declination in degrees (east positive).
// TODO: look up the real value for Otto's location and set it here.
constexpr float COMPASS_DECLINATION_DEG = 0.0f;

// SPI0: 2x GC9A01 displays, 7-pin variant (VCC/GND/SCL/SDA/DC/CS/RST,
// no BLK pin — backlight is wired internally to VCC, always on)
// RST hardwired to 3.3V.
constexpr int OTTO_PIN_SPI0_SCK = 10;
constexpr int OTTO_PIN_SPI0_MOSI = 11;
constexpr int OTTO_PIN_SPI0_DC = 12;
constexpr int OTTO_PIN_SPI0_CS1 = 13;
constexpr int OTTO_PIN_SPI0_CS2 = 14;

// I2S (PIO): INMP441 microphone
constexpr int OTTO_PIN_I2S_BCLK = 15;
constexpr int OTTO_PIN_I2S_WS = 16;
constexpr int OTTO_PIN_I2S_SD = 17;

// GPS Neo-6M (RX only, broadcasts NMEA unprompted)
constexpr int OTTO_PIN_GPS_RX = 18;

// Radar HLK-LD2402 (PIO UART; module pin "IO" = fast presence GPIO,
// independent of the UART data stream, in addition to TX/RX. Module
// powered at 3.3V, not 5V, so IO/TX/RX are 3.3V-level by construction)
constexpr int OTTO_PIN_RADAR_TX = 19;
constexpr int OTTO_PIN_RADAR_RX = 20;
constexpr int OTTO_PIN_RADAR_OUT = 22;  // module pin "IO"

// DFPlayer Mini (PIO UART), replaces the WT588D. Controlled via UART
// commands (play track N from microSD), not parallel trigger lines.
// Powered at 5V for full amplifier output; TX (Pico->module) needs a
// ~1k series resistor, RX (module->Pico) needs a voltage divider
// (module TX is 5V logic, GPIO max is 3.3V) — see wiring-reference.md.
constexpr int OTTO_PIN_DFPLAYER_TX = 21;
constexpr int OTTO_PIN_DFPLAYER_RX = 0;

// Head servo (MG995, ~180 deg): PWM 50 Hz, 1-2 ms pulse. 5V from the logic
// rail via connector J1 (1000uF cap); stall current ~1.4A — ramp moves.
constexpr int OTTO_PIN_SERVO_HEAD = 1;

// Analog sensors (ADC, 3.3V-powered): rain sensor AO, photoresistor divider
constexpr int OTTO_PIN_RAIN_ADC = 26;   // ADC0, MH-RD module AO (DO unconnected)
constexpr int OTTO_PIN_PHOTO_ADC = 27;  // ADC1, 3.3V - 10k - node - LDR - GND

// Spare: GP3, GP4, GP6, GP7 (freed by the PCF8574P direction lines) and
// GP28 (ADC2) — kept free for future expansion.

// --- Drive tuning ---
// TODO: measure and set the real track width (distance between wheel centers).
constexpr float TRACK_WIDTH_MM = 200.0f;

// 5840-31ZY worm-gear motor, 12V/40RPM, with a 180mm wheel:
// circumference (pi * 180mm) * (40 RPM / 60) = ~377mm/s no-load top speed.
// Actual top speed under load will be lower; treat as an upper bound.
constexpr float MAX_SPEED_MM_S = 377.0f;
constexpr int PWM_MAX = 255;

// --- Protocol / safety ---
constexpr unsigned long DRIVE_COMMAND_TIMEOUT_MS = 500;
constexpr unsigned long TELEMETRY_INTERVAL_MS = 100;
constexpr unsigned long SERIAL_BAUD = 115200;
// Hardware watchdog: resets the RP2040 if loop() stops running (e.g. hung
// bus). Must be > the worst-case loop time. Motor EN pins fall back to
// inputs on reset, so the drivers' EN pull-downs/jumpers define the idle state.
constexpr uint32_t HW_WATCHDOG_MS = 1000;
// I2C transfers give up after this long instead of blocking loop().
constexpr uint32_t I2C_TIMEOUT_MS = 25;

// Speed used by the single-letter manual test commands (w/a/s/d), mm/s.
constexpr float TEST_SPEED_MM_S = 150.0f;
