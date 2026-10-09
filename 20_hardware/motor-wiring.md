# Otto — Motor Wiring (2× L298N, Parallel-Bridge Mode)

Carried over from the previous ESP32-based `hermann` platform (see
[`hermann/1_remote_control/src/remote_control/drive.h`](../../hermann/1_remote_control/src/remote_control/drive.h)):
each motor gets its own L298N board, with **both internal H-bridges of that
board wired in parallel** (L298N datasheet p.8) to raise the per-motor
current rating from ~2A (single bridge) to ~3–4A. This is not "one L298N
per side, two motors each" — it's two boards, one motor each, each board
running both its bridges in lockstep for the one motor.

## Per-board jumpering (do this on each of the 2 L298N boards, before wiring to the RP2040)

| Board pins | Jumper together | Goes to |
| --- | --- | --- |
| OUT1 + OUT4 | tie with a wire | Motor terminal A |
| OUT2 + OUT3 | tie with a wire | Motor terminal B |
| IN1 + IN4 | tie with a wire | direction signal 1 (PCF8574P port) |
| IN2 + IN3 | tie with a wire | direction signal 2 (PCF8574P port) |
| ENA + ENB | tie with a wire | RP2040 PWM pin |

Both bridges must switch and PWM in lockstep — if ENA/ENB or the IN pairs
end up on separate RP2040 GPIOs and drift out of sync (even briefly), the
two bridges fight each other. Tie them physically on the board, drive each
pair from a single signal (one GPIO for EN, one PCF8574P port per IN pair).

**Optional: remove the L298N's onboard 5V-regulator jumper.** The regulator
only supplies the chip's own logic (IN/EN pins) — a few mA — so the
paralleled bridges' 3–4A motor current doesn't load it any harder than a
single-bridge setup; that's not a reason to pull the jumper. The actual
concern is input voltage: these onboard regulators (typically 7805-style)
are usually rated to ~12V in, and a 3S LiPo sits right at/above that
(11.1V nominal, up to ~12.6V full charge). If the `hermann` platform ran
the same board/battery combination with the jumper in place without
issues, it's fine to leave it — otherwise, pull the jumper and feed the
board's logic-5V pin from a separate, clean 5V source instead (see Power
below).

## Pin mapping (RP2040 + PCF8574P)

Matches [`Config.h`](../30_spine/spine/Config.h):

| Signal | Pin | L298N board | Jumpered pins |
| --- | --- | --- | --- |
| Motor L — PWM enable | GP2 | #1 (left) | ENA+ENB |
| Motor L — dir 1 | PCF8574P P2 | #1 (left) | IN1+IN4 |
| Motor L — dir 2 | PCF8574P P3 | #1 (left) | IN2+IN3 |
| Motor R — PWM enable | GP5 | #2 (right) | ENA+ENB |
| Motor R — dir 1 | PCF8574P P4 | #2 (right) | IN1+IN4 |
| Motor R — dir 2 | PCF8574P P5 | #2 (right) | IN2+IN3 |

Direction goes over I2C (PCF8574P, 0x20). Only EN is a native pin, so
stopping (EN low) never depends on I2C. Add a 4.7–10 kΩ pull-up to 3.3 V on
each direction line (the PCF8574P only sources ~100 µA per pin, two L298N
inputs hang on each line) and a 10 kΩ pull-down on each EN. Check the
boards for onboard pull-downs on IN1–IN4 — they can pull the high level
below the L298N's 2.3 V threshold. Details in
[`wiring-reference.md`](wiring-reference.md).

## Power

- **VMS (motor supply)**: battery pack (3S LiPo per the `hermann` hardware
  doc) to both boards' VMS/+12V screw terminal, in parallel. Common
  negative rail.
- **Logic 5V**: normally the onboard regulator (jumper in place) is fine —
  see the input-voltage caveat above. Only if you pull the jumper: feed
  the board's logic-5V pin from a separate, clean 5V source instead (RP2040
  VBUS/USB works, since the L298N's IN/EN pins draw negligible current).
- **GND**: battery ground, both L298N boards' logic ground, and RP2040
  GND must all be tied together. Without a common ground the direction/PWM
  signals are undefined and the motors will behave erratically.

## Current headroom — caveat

Paralleling both bridges roughly doubles the *per-channel* rating, but the
L298N chip itself still has a package-level thermal limit. Treat ~3–4A as
a short-burst peak, not sustained current — use a heatsink on both boards,
and if the 5840-31ZY's actual stall current (check the datasheet/measure
it) sits close to or above that, a MOSFET-based driver (e.g. a BTS7960 or
similar) would have more headroom than the L298N. Not a blocker for now,
just something to watch if the motors stall under load (e.g. climbing,
snagging on grass).
