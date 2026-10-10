# Otto Spine — Wiring Reference (KiCad-Grundlage)

Vollständige Pin-/Netzliste für den RP2040-Teil (`spine`), Stand wie in
[`Config.h`](../30_spine/spine/Config.h) und
[`10_concepts/otto-concept.md`](../10_concepts/otto-concept.md) festgelegt.
Gedacht als Grundlage für einen Schaltplan in KiCad — Bauteil für Bauteil,
Netz für Netz.

## Vorschlag Blattstruktur (Hierarchical Sheets)

Bei der Bauteilzahl lohnt sich eine Aufteilung in mehrere Sheets statt
einem großen Blatt:

1. `spine-core` — RP2040 (Pico), Stromversorgung
2. `motors` — 2× L298N (je 1 pro Motor, H-Brücken parallel, siehe `motor-wiring.md`); EN am Pico, IN1/IN2 am PCF8574P
3. `i2c-bus` — GY-273 (Kompass, auf dem Deck), 1× PCF8574P (Vibration, DFPlayer-BUSY)
4. `displays` — 2× GC9A01 (SPI0)
5. `audio` — INMP441 (I2S), DFPlayer Mini + Lautsprecher (PIO-UART)
6. `nav-sensors` — GPS Neo-6M, HLK-LD2402 Radar

## Stromversorgung / Domains

| Domain | Spannung | Versorgt | Quelle |
| --- | --- | --- | --- |
| Motor-Rail | 12V | 2× 5840-31ZY über je 1 L298N-Board (VS, parallel) | Akku direkt |
| Jetson-Rail | 19V | Jetson Orin Nano Devkit (Hohlstecker 5,5×2,5mm) | dediziertes 12V→19V-Boost-Modul, **≥5A Dauerstrom, eigener Kühlkörper/Lüfter** — das vorhandene XL6009-Modul (Chip-Grenze ~4A, kein Kühlkörper) reicht nicht für das volle 65W-Budget der offiziellen 19V/3,42A-Versorgung, siehe Offene Punkte unten |
| Logik-Rail | 5V | GPS Neo-6M, DFPlayer Mini+Lautsprecher, Kopf-Servo (V+), **plus Eingangsstrom des externen 3,3V-Reglers** (siehe Zeile unten — der hängt selbst an dieser 5V-Rail) | eigener 5V/3A-Buck-Regler, **getrennt vom L298N-Onboard-Regler** (siehe Strombudget-Diskussion — Motorlast soll Sensorik nicht einbrechen lassen) |
| 3.3V-Rail (Pico-intern) | 3.3V | **nur** der RP2040-Chip selbst | Pico-Onboard-Regler (VSYS→3V3) — lässt sich nicht abschalten/umgehen, solange die native USB-Verbindung zum Jetson besteht (VBUS aktiviert VSYS über die interne Diode, der Regler läuft zwangsläufig mit); Last ist mit ~30-50mA aber trivial gegenüber der 300mA-Grenze |
| 3.3V-Rail (extern) | 3.3V | GY-273, INMP441, 1× PCF8574P, Regensensor, Vibrationssensor, Fotowiderstand-Teiler, 2× GC9A01, HLK-LD2402 | eigener 3.3V/1A-Standardregler von der 5V-Rail abgeleitet — **alle** 3.3V-Peripherie außer dem RP2040-Chip selbst, nicht der Pico-Onboard-Regler. Worst-Case-Summe (~110-180mA Displays+Radar + ~106mA restliche Sensorik) bleibt mit großem Abstand unter 1A. |
| GND | — | gemeinsame Masse für alle Domains | Sternpunkt am Akku-Minus empfohlen |

**Warum nicht komplett ohne Pico-Regler:** der RP2040-Chip selbst lässt
sich elektrisch nicht vom Onboard-Regler trennen, solange USB (Jetson-
Link) angeschlossen ist — zwei Regler, die denselben 3V3-Netzknoten
treiben, würden sich gegenseitig belasten (Kreisströme, im schlimmsten
Fall Beschädigung). Die einzig saubere Lösung ist die hier gewählte:
Onboard-Regler bleibt für den RP2040-Chip zuständig (trivial kleine
Last), alle anderen 3.3V-Verbraucher laufen komplett getrennt über den
externen Regler.

**5V nicht vom Pico-USB-Anschluss abgreifen:** VBUS (Pin 40) führt zwar
technisch die 5V vom USB-Kabel als eigenen Pin heraus, aber das ist die
Versorgung des **Jetson-USB-Ports**, nicht des Akkus — USB-Ports sind
auf 500mA (USB 2.0) bis 900mA (USB 3.0) limitiert. Die Logik-Rail
braucht im Worst-Case (DFPlayer bei hoher Lautstärke, ~570-970mA) schon
allein grenzwertig bis mehr als das, ganz ohne Reserve für Lastspitzen
oder USB-2.0-Ports — würde die USB-Strombegrenzung des Jetson
ansprechen, bräche die Verbindung ab, über die auch die Fahrbefehle
laufen. Deshalb eigener 5V/3A-Buck-Wandler direkt vom Akku, nicht vom
USB-Pfad abgezweigt (siehe otto-concept.md für die Strombudget-Tabelle
und warum 3A reicht — dort noch mit 2A gerechnet, vor Kopf-Servo MG995).

GC9A01 laut Datenblatt (1,28" 240×240, 7-Pin-Modul, kein BLK):
Arbeitsspannung 2,8–3,3V, **nicht 5V-tolerant**. HLK-LD2402 laut
Herstellerbeschreibung mit 3,0–3,6V betrieben (statt 5V) — dadurch ist
der TX/RX/IO-Ausgangspegel zwangsläufig auf 3,3V begrenzt (kann die
eigene Versorgungsspannung nicht überschreiten), eine Pegelmessung vor
dem Anschließen an GP19/GP20/GP22 entfällt damit. Beide Geräte zusammen
an der externen 3.3V-Rail statt am Pico-Onboard-Regler, siehe Offene
Punkte unten.

## RP2040 (Raspberry Pi Pico) — Pin-Map

| GPIO | Netz-Name | Richtung | Verbunden mit |
| --- | --- | --- | --- |
| GP0 | DFPLAYER_RX | in (PIO-UART, über Spannungsteiler) | DFPlayer Mini TX |
| GP1 | SERVO_HEAD | out (PWM, Slice 0 / Kanal B) | Kopf-Servo MG995 Signal (J1 Pin 2) |
| GP2 | M_L_EN | out (PWM) | L298N ENA+ENB (links) |
| GP3 | — | — | frei (No-Connect; Richtung jetzt am PCF8574P) |
| GP4 | — | — | frei (No-Connect) |
| GP5 | M_R_EN | out (PWM) | L298N ENA+ENB (rechts) |
| GP6 | — | — | frei (No-Connect) |
| GP7 | — | — | frei (No-Connect) |
| GP8 | I2C0_SDA | bidir | SDA: GY-273, PCF8574 (gemeinsamer Bus) |
| GP9 | I2C0_SCL | bidir | SCL: GY-273, PCF8574 (gemeinsamer Bus) |
| GP10 | SPI0_SCK | out | GC9A01 #1 SCK, GC9A01 #2 SCK (gemeinsam) |
| GP11 | SPI0_MOSI | out | GC9A01 #1 SDA/MOSI, GC9A01 #2 SDA/MOSI (gemeinsam) |
| GP12 | SPI0_DC | out | GC9A01 #1 DC, GC9A01 #2 DC (gemeinsam) |
| GP13 | SPI0_CS1 | out | GC9A01 #1 CS |
| GP14 | SPI0_CS2 | out | GC9A01 #2 CS |
| GP15 | I2S_BCLK | out | INMP441 SCK |
| GP16 | I2S_WS | out | INMP441 WS |
| GP17 | I2S_SD | in | INMP441 SD |
| GP18 | GPS_RX | in | GPS Neo-6M TX (Pico empfängt nur, sendet nichts) |
| GP19 | RADAR_TX | out (PIO-UART) | HLK-LD2402 RX |
| GP20 | RADAR_RX | in (PIO-UART) | HLK-LD2402 TX |
| GP21 | DFPLAYER_TX | out (PIO-UART, über Vorwiderstand) | DFPlayer Mini RX |
| GP22 | RADAR_OUT | in | HLK-LD2402 IO (schneller Presence-Ausgang, unabhängig vom UART) |
| GP26 | RAIN_SIGNAL | in (ADC0) | Regensensor AO (analog) |
| GP27 | PHOTO_R | in (ADC1) | Fotowiderstand-Spannungsteiler (Mittelpunkt R6/R7) |
| GP28 | — | — | frei (ADC-fähig, No-Connect) |

**Farbsensoren (TCS3200, TCS34725) sind aus der Beschreibung entfernt**
(vorerst nicht verbaut) — der TCS34725-I2C-Eintrag entfällt ersatzlos.
**WT588D ersetzt durch DFPlayer Mini** (UART-gesteuert statt
Trigger-Leitungen) — GP21 war zuvor der direkte TCS3200_OUT-Pin und trägt
jetzt DFPLAYER_TX, GP0 (zuvor für den Vibrationssensor direkt genutzt)
trägt jetzt DFPLAYER_RX. Der Vibrationssensor ist dafür **zurück auf den
PCF8574P** verschoben (siehe Portbelegung unten) — der Chip bleibt im
Design, jetzt für einfache I/O-Aufgaben statt Audio-Trigger. Der
Regensensor wird **analog** über GP26 (ADC0) gelesen, der Fotowiderstand
über GP27 (ADC1).

GC9A01-Modul ist die 7-Pin-Variante (VCC/GND/SCL/SDA/DC/CS/RST, **kein
BLK-Pin**) — die Hintergrundbeleuchtung ist intern fest mit VCC
verdrahtet, immer an, nicht per GPIO schaltbar/dimmbar. RST liegt laut
Konzept fest auf 3.3V (kein Software-Reset über den RP2040) — beim
Schaltplan entsprechend als Netz auf die 3.3V-Rail statt auf einen GPIO
legen.

HLK-LD2402-IO bewusst auf GP22 statt auf einen der GP26–28-Pins gelegt:
das sind die einzigen ADC-fähigen Pins am RP2040 — GP26 (Regen) und GP27
(Fotowiderstand) sind jetzt belegt, GP28 bleibt für eine spätere analoge
Erweiterung frei und soll nicht für ein rein digitales Signal
verbraucht werden.

## I2C0-Bus — Adressen

Ein gemeinsamer Bus (GP8/GP9), beide Teilnehmer (GY-273 und PCF8574P)
sitzen auf dem Deck, kurze Leitungen. Pull-ups (R1/R2, 4.7kΩ, SDA→3.3V
und SCL→3.3V) einmal auf dem Bus, nicht pro Modul (sonst zu niederohmig) — nur ergänzen, falls keines der Module schon eigene
Pull-ups mitbringt (vorher mit Multimeter gegen 3.3V prüfen).

| Gerät | I2C-Adresse | Hinweis |
| --- | --- | --- |
| GY-273 (hier: QMC5883P, per I2C-Scan; HMC5883L-Variante wäre 0x1E) | 0x2C | fest |
| PCF8574 | 0x20 | A0=GND, A1=GND, A2=GND — Default-Adresse, alle Jumper unverändert lassen |

Mit nur noch einem PCF8574 im Design (Farbsensoren entfernt, WT588D
braucht ohnehin den ganzen Chip) ist keine Adressumschaltung mehr nötig
— der Chip bleibt auf seiner werksseitigen Default-Adresse 0x20, kein
Jumper zu brücken.

**PCF8574-Adresspins (A0–A2):** trotzdem alle drei Pins fest auf GND oder
VCC lassen (nicht offen) — normale CMOS-Digitaleingänge, ein floatender
Pin liefert ein undefiniertes Bit und macht die I2C-Adresse instabil.
Bestätigt: verbautes Bauteil ist der **PCF8574P** (NXP, DIP-Gehäuse,
Standard-Variante) — Adressbasis 0x20. (Die PCF8574A-Variante mit Basis
0x38 kommt hier nicht zum Einsatz.)

**PCF8574-INT-Pin:** offener Drain, aktiv-low, wird von der Chip-internen
Logik gezogen, wenn sich ein Eingangs-Port ändert. Da wir die Ports per
Software-Polling lesen (kein Interrupt-getriebenes Einlesen), bleibt INT
**unbeschaltet (NC)** — kein Pull-up nötig, da der Pin so nirgends
angeschlossen ist und dadurch keine Wirkung hat.

## PCF8574 (0x20) — Portbelegung

Der PCF8574P trägt Vibrationssensor, DFPlayer-BUSY und — seit der
Auslagerung von den RP2040-Pins — die vier **Richtungsleitungen der
L298N-Boards**. 6 von 8 Leitungen belegt, P6/P7 frei. Der Regensensor
hängt nicht am Expander (analog an GP26).

| Port | Netz | Richtung | Ziel |
| --- | --- | --- | --- |
| P0 | VIBRATION_SIGNAL | in | Erschütterungssensor Digital-Out |
| P1 | DFPLAYER_BUSY | in | DFPlayer Mini BUSY-Ausgang (aktiv-low während Wiedergabe) |
| P2 | M_L_DIR1 | out | L298N links IN1+IN4 |
| P3 | M_L_DIR2 | out | L298N links IN2+IN3 |
| P4 | M_R_DIR1 | out | L298N rechts IN1+IN4 |
| P5 | M_R_DIR2 | out | L298N rechts IN2+IN3 |
| P6–P7 | — | — | frei (No-Connect im Schaltplan) |

**Motor-Richtung über I2C — Randbedingungen:**
- **Stopp bleibt unabhängig von I2C:** EN (GP2/GP5) sind native Pins, Stopp =
  EN low. Ein I2C-Fehler kann keinen Motor am Laufen halten. EN zusätzlich
  mit 10 kΩ nach GND (Pull-down) absichern.
- **Ein Schreibzugriff (~200 µs bei 100 kHz)** setzt alle vier
  Richtungsbits; der Chip ist für 100 kHz spezifiziert. Reihenfolge beim
  Umschalten: EN 0 → Richtung → EN wieder hoch. P0/P1/P6/P7 müssen im
  Schreibbyte auf 1 bleiben (Schattenregister im Code).
- **Refresh:** Das Richtungsbyte wird alle 20 ms erneut gesendet, damit ein
  gestörter Transfer (Motorstörungen auf SDA/SCL) sich selbst heilt.
- **Pegel:** Der PCF8574P liefert High nur über eine schwache Stromquelle
  (~100 µA), an jeder Leitung hängen zwei L298N-Eingänge. **Je einen
  4,7–10 kΩ Pull-up nach 3,3 V an P2–P5 vorsehen** und prüfen, ob die
  L298N-Boards Pull-downs an IN1–IN4 haben (Teiler kann unter die
  L298N-High-Schwelle von 2,3 V fallen → dann Puffer statt Pull-up).
- **Power-on:** Der PCF8574P startet mit allen Ports high (IN1=IN2=1 = Bremse),
  solange EN low ist, bleibt die Brücke aber aus.

**Versorgung Regen-/Vibrationssensor:** beide an der **3.3V-Rail**
(gleiche Schiene wie der PCF8574P selbst), nicht 5V. Beide sind
LM393-Komparator-Module (MH-RD bzw. SW-420-artig) — bei 5V-Versorgung
läge der Digital-High-Pegel des SW-420 bei ~5V und würde den
PCF8574-Eingang überspannen, der Regensensor-AO den ADC des RP2040
(analog zum HLK-LD2402-Problem). 3,3V-Versorgung vermeidet das ohne
Spannungsteiler. Regensensor: nur **AO → GP26**, DO bleibt unbeschaltet. Zu prüfen beim
Aufbau: das Schwellwert-Trimm-Poti auf diesen Modulen ist oft für
5V-Betrieb kalibriert — bei 3,3V ggf. nachjustieren, damit der
Digitalausgang zuverlässig kippt.

## Analog — Regensensor & Fotowiderstand (ADC)

| Signal | Pico-Pin | Beschaltung |
| --- | --- | --- |
| RAIN_SIGNAL | GP26 (ADC0) | Regensensor AO direkt (Modul an 3.3V, DO unbeschaltet) |
| PHOTO_R | GP27 (ADC1) | Spannungsteiler: 3.3V → R7 (10kΩ) → Mittelpunkt (PHOTO_R) → R6 (Fotowiderstand, z.B. GL5528) → GND |

ADC_VREF ist mit C1 (220nF) nach GND entkoppelt (siehe Pico-Pins ohne
Signalnetz). Der Fotowiderstand sitzt außen (Kabel JST-XH 2), R7 auf der
Platine. Bei hellem Licht sinkt R6 → PHOTO_R steigt Richtung 3.3V.

## SPI0 — Displays (GC9A01 ×2)

Gemeinsamer Bus (SCK/MOSI/DC), individuelle CS-Leitung pro Display.
GC9A01 hat keinen MISO (write-only), daher kein MISO-Netz nötig.
Verbautes Modul: 7-Pin-Variante (VCC/GND/SCL/SDA/DC/CS/RST) — **kein
BLK-Pin**, Hintergrundbeleuchtung intern fest auf VCC, immer an.

| Display-Pin | Netz | Display 1 | Display 2 |
| --- | --- | --- | --- |
| SCL/SCK | SPI0_SCK | GP10 | GP10 (gemeinsam) |
| SDA/MOSI | SPI0_MOSI | GP11 | GP11 (gemeinsam) |
| DC | SPI0_DC | GP12 | GP12 (gemeinsam) |
| CS | — | GP13 | GP14 |
| RST | — | 3.3V (fest) | 3.3V (fest) |
| VCC | — | 3.3V-Rail extern (2,8–3,3V lt. Datenblatt, nicht 5V-tolerant) | 3.3V-Rail extern (2,8–3,3V lt. Datenblatt, nicht 5V-tolerant) |

## I2S — INMP441 Mikrofon

| INMP441-Pin | Netz | Verbunden mit |
| --- | --- | --- |
| SCK (BCLK) | I2S_BCLK | GP15 |
| WS | I2S_WS | GP16 |
| SD | I2S_SD | GP17 |
| L/R | — | GND (Kanalwahl: links) |
| VDD | — | 3.3V-Rail extern |

## UART — GPS & Radar (beide PIO-emuliert außer wo nativ)

| Gerät | Pico-Pin | Richtung | Bemerkung |
| --- | --- | --- | --- |
| GPS Neo-6M TX | GP18 | Pico RX | NMEA, unaufgefordert gesendet; GPS-RX nicht verbunden |
| HLK-LD2402 RX | GP19 | Pico TX (PIO-UART) | Standard-Baudrate vermutlich 115200 — beim ersten Anschließen verifizieren |
| HLK-LD2402 TX | GP20 | Pico RX (PIO-UART) | |
| HLK-LD2402 IO | GP22 | Pico-Eingang (digital) | Presence-Signal, unabhängig vom UART-Datenstrom; bewusst nicht auf GP26-28 (ADC-fähig, bleiben frei) |

Pin-Beschriftung auf dem konkreten Modul (ICGOICIC HLK-LD2402-V1.0,
5-Pin-Header): **V, IO, G, TX, RX**. "IO" entspricht dem generisch als
OT1 bezeichneten Presence-Ausgang anderer Datenblätter.

**HLK-LD2402 Versorgung/Logikpegel — Entscheidung:** Modul mit **V=3,3V**
betreiben (offiziell unterstützter Bereich 3,0–3,6V laut
Produktbeschreibung, Ø-Strom ~50mA), nicht mit 5V. Damit ist der
TX/RX/IO-Ausgangspegel automatisch auf 3,3V begrenzt — ein
Digitalausgang kann seine eigene Versorgungsspannung nicht überschreiten
—, eine Pegelmessung vor dem Anschließen an GP19/GP20/GP27 entfällt. Die
3,3V-Versorgung kommt dabei von der **externen** 3.3V-LDO-Stufe (siehe
Stromversorgung oben), nicht vom Pico-Onboard-Regler, um dessen knappe
~300mA-Grenze nicht zusätzlich zu belasten.

## UART — DFPlayer Mini (Audio, ersetzt WT588D)

Ersetzt das WT588D (Parallel-/Key-Trigger) durch ein UART-gesteuertes
Modul: Track abspielen per Kommando (z.B. "spiele Track 0007"), Sounds
liegen als `0001.mp3`, `0002.mp3`, ... auf einer microSD-Karte — kein
Trigger-Pin-Budget, keine Kombinations-Adressierung nötig.

| Gerät | Pico-Pin | Richtung | Bemerkung |
| --- | --- | --- | --- |
| DFPlayer Mini RX | GP21 (PIO-UART) | Pico TX | über ~1kΩ-Vorwiderstand (siehe unten) |
| DFPlayer Mini TX | GP0 (PIO-UART) | Pico RX | über Spannungsteiler (siehe unten) |

**Versorgung/Logikpegel — Entscheidung:** Modul mit **5V** betreiben
(unterstützt 3,2–5,0V; 5V für vollen Verstärker-Headroom/Lautstärke,
~3W an 4-8Ω-Lautsprecher). Damit liegt die TX-Ausgangsspannung des
Moduls bei 5V-Pegel — zu hoch für die 3,3V-GPIOs des RP2040, im
Unterschied zur HLK-LD2402-Lösung (dort mit 3,3V betrieben) ist hier
also aktive Pegelanpassung nötig:

- **Pico-TX (GP21) → DFPlayer-RX:** ein Vorwiderstand (~1kΩ) in Reihe
  reicht — das Modul erkennt 3,3V-Pegel am RX zuverlässig als High,
  der Widerstand ist reine Strombegrenzung/Sicherheitsmarge, kein
  echter Spannungsteiler nötig.
- **DFPlayer-TX → Pico-RX (GP0):** hier **ist** ein echter
  Spannungsteiler nötig, da sonst 5V direkt auf einen 3,3V-GPIO
  träfen. Beispielwerte: 1kΩ (DFPlayer-TX → Knotenpunkt), 2kΩ
  (Knotenpunkt → GND), Abgriff am Knotenpunkt → GP0. Ergibt
  5V × 2k/(1k+2k) ≈ 3,33V — im sicheren Bereich für den RP2040.

Im Schaltplan als R3 (Vorwiderstand, Pico→Modul) und R4/R5 (Teiler,
Modul→Pico) umgesetzt. **Zu prüfen:** falls R4/R5 beide 1kΩ sind, ergibt
das nur 5V × 1k/(1k+1k) = 2,5V — knapp über der garantierten
Logic-High-Schwelle des RP2040 (~2,3V bei 3,3V VDDIO), wenig
Rauschreserve. Ungleiches Verhältnis (z.B. 1k/2k → 3,33V) ist sicherer.
Außerdem gegenchecken, dass der **einzelne** Widerstand (R3) auf der
Leitung Pico→Modul sitzt und der **Teiler** (R4+R5) auf der Leitung
Modul→Pico — vertauscht würde GP0 nicht geschützt.

**Update — BUSY-Pin doch verdrahtet:** abweichend von der ursprünglichen
"nur UART"-Entscheidung ist der DFPlayer-BUSY-Ausgang jetzt an
PCF8574-Port P1 angeschlossen (siehe PCF8574-Portbelegung oben) — liefert
einen schnellen "spielt gerade"-Status ohne UART-Query.

## Motoren — 2× L298N (ein Board pro Motor, H-Brücken parallel)

Volle Herleitung, Jumpering und Power-Diagramm siehe
[`motor-wiring.md`](motor-wiring.md) — hier nur die Netzliste. **Kein**
gemeinsamer 2-Kanal-Treiber: jeder Motor bekommt ein eigenes L298N-Board,
auf dem beide internen H-Brücken parallel gejumpert sind (höherer
Stromrating pro Motor). Beide Brücken eines Boards hängen daher jeweils
am selben Signal (EN am RP2040-Pin, IN1/IN2 am PCF8574P-Port).

| RP2040-Pin | Netz | Board | Gejumperte Board-Pins |
| --- | --- | --- | --- |
| GP2 | M_L_EN | #1 (links) | ENA+ENB |
| PCF8574P P2 | M_L_DIR1 | #1 (links) | IN1+IN4 |
| PCF8574P P3 | M_L_DIR2 | #1 (links) | IN2+IN3 |
| GP5 | M_R_EN | #2 (rechts) | ENA+ENB |
| PCF8574P P4 | M_R_DIR1 | #2 (rechts) | IN1+IN4 |
| PCF8574P P5 | M_R_DIR2 | #2 (rechts) | IN2+IN3 |

| Board-Pin (beide Boards) | Verbunden mit |
| --- | --- |
| OUT1+OUT4 (gejumpert) | Motor-Anschluss A |
| OUT2+OUT3 (gejumpert) | Motor-Anschluss B |
| VS (Motorversorgung) | 12V-Rail (Motor-Akku), beide Boards parallel |
| GND | gemeinsame Masse |
| Logik-5V-Pin | Onboard-Regler-Jumper bleibt **gesetzt** (lief beim Vorgängerbau `hermann` mit derselben Board/Akku-Kombination problemlos) — Entfernen ist optional, kein Muss, siehe `motor-wiring.md` |

## Jetson-Link

Natives USB (USB-CDC, `Serial`) am Pico-USB-Anschluss — kein GPIO-Netz,
kein UART0-Verdrahtungsbedarf (siehe otto-concept.md-Korrektur).

## Pico-Pins ohne Signalnetz — Entscheidungen

Aus der KiCad-Schaltplanprüfung (Raspberry Pi Pico W-Symbol):

| Pin(s) | Entscheidung |
| --- | --- |
| GPIO0 | Belegt: DFPLAYER_RX. |
| GPIO1 | Belegt: SERVO_HEAD (Kopf-Servo MG995). Im Schaltplan korrekt verbunden. |
| GPIO26/27 (ADC0/1) | Belegt: GP26 = RAIN_SIGNAL, GP27 = PHOTO_R (siehe Abschnitt Analog). |
| GPIO28 (ADC2) | Reserve für spätere Analogsensoren — nur **No-Connect-Flag**, kein Header. |
| SWCLK, SWDIO | Unbeschaltet, kein SWD-Debug-Header geplant — Flashing läuft ausschließlich über USB/BOOTSEL. |
| 3V3_EN | Unbeschaltet — kein Power-Enable-Schalter, Pin ist auf dem Pico-Modul bereits intern hochgezogen. |
| **RUN** | **Reset-Taster ergänzen**: Taster (normally-open) zwischen RUN und GND, kein externer Pull-up nötig (auf dem Pico-W-Modul bereits vorhanden, ~50-100kΩ intern). Kurzschluss RUN→GND löst einen Reset aus, ohne das USB-Kabel abziehen zu müssen. |
| ADC_VREF | C1 = 220nF nach GND (ADC-Rauschunterdrückung), im Schaltplan vorhanden. |
| TP1–TP6 (USB_GND/DM/DP, SMPS_PS, LED_OUT, BOOTSEL), AGND | Bereits vorhandene Testpads auf dem physischen Pico-W-Modul bzw. korrekt an GND — keine Aktion nötig. |

## Sensor-Steckbrief — Stecker, Versorgung, Strom

Zusammenfassung pro Einbauort (Kopf drehbar / Deck / Mast). Ergänzt die
Pin-Map oben um Steckertyp, Versorgungsspannung und Stromaufnahme.
Stromwerte sind typische Datenblatt-/Erfahrungswerte, mit „Schätzung"
markierte Werte beim Aufbau nachmessen (V&A-Meter).

### Kopf (drehbar, alles per Kabel zum Deck)

| Sensor | Schnittstelle | Signale | Stecker | Versorgung | Strom typ. / max. |
| --- | --- | --- | --- | --- | --- |
| INMP441 Mikrofon | I2S | SCK, WS, SD (L/R im Kopf auf GND) | JST-XH 5 | 3,3 V | ~1,5 mA |
| HLK-LD2402 Radar | UART + OUT | TX, RX, OUT | JST-XH 5 | 3,3 V | ~40–60 mA (Schätzung) |
| GPS Neo-6M (GY-NEO6MV2) | UART | TX (Pico-seitig RX; GPS-RX unbeschaltet) | JST-XH 3/4 | 5 V (Onboard-LDO) | ~35 mA Tracking / ~50 mA Akquise |
| 2× GC9A01 Display (7-Pin, ohne BLK) | SPI | SCK, MOSI, DC (gemeinsam), CS1, CS2; RST fest auf 3,3 V am Display | JST-XH 7 (SCK, MOSI, DC, CS1, CS2, VCC, GND) | 3,3 V | je ~20–30 mA → ~60 mA |
| USB-Webcam | USB → Jetson | – | USB-Kabel | 5 V vom Jetson | ~150–300 mA |

Der **Kompass GY-273 sitzt nicht mehr im Kopf**, sondern auf dem Deck
(siehe unten).

### Deck (gemeinsame Hauptplatine)

| Komponente | Anbindung | Stecker | Versorgung | Strom |
| --- | --- | --- | --- | --- |
| RP2040 (Pico W) | – | auf Platine | 3,3 V (Onboard-Regler) | ~30–50 mA |
| PCF8574P GPIO-Expander (0x20; Motor-Richtung, Vibration, BUSY) | I2C (GP8/GP9) | auf Platine | 3,3 V | < 1 mA |
| GY-273 Kompass (HMC5883L, 0x1E) | I2C (GP8/GP9) | auf Platine / JST-XH 4 | 3,3 V | < 1 mA |
| SW-420 Vibration | DO → PCF8574P P0 (Polling) | direkt auf Platine | 3,3 V | ~5–10 mA |
| Regensensor | AO → GP26 (ADC0); DO unbeschaltet | Sensorplatte außen, JST-XH 2 | 3,3 V | ~5–15 mA, nur beim Messen |
| DFPlayer Mini | UART (GP21 TX über R3 1k, GP0 RX über Teiler R4 1k/R5 2k) + BUSY → PCF8574P P1 | auf Platine; Lautsprecher JST-XH 2 | 5 V | ~20 mA Ruhe / ~300–500 mA Peak (je nach Lautsprecher) |
| Fotowiderstand (z. B. GL5528) | Teiler 3,3 V → R7 10k → PHOTO_R → R6 (LDR) → GND, Mittelpunkt → GP27 (ADC1) | LDR außen, JST-XH 2; R7 auf Platine | 3,3 V | < 0,5 mA |

**Kompass-Einbau:** GY-273 auf dem Deck **mit Abstand zu den Motoren, den
L298N-Boards und den dicken 12V-Motorleitungen** platzieren (Magnetfelder
verfälschen den HMC5883L). Möglichst weit vorn/hinten oder oben an der
Deck-Ecke, weg vom Akku-Strompfad, plan ausgerichtet; mit den
Motoren in Betrieb kalibrieren (Hard-/Soft-Iron). Vorteil gegenüber dem
drehbaren Kopf: Fahrzeug-Orientierung ohne Kopfwinkel, kurze I2C-Leitung.

### Kopfantrieb (Deck)

| Komponente | Anbindung | Stecker | Versorgung | Strom |
| --- | --- | --- | --- | --- |
| Kopf-Servo MG995 (Drehung) | PWM (50 Hz) von GP1 (SERVO_HEAD), 3,3-V-Pegel | J1 „Servo Head", JST-XH 3 (1 = +5 V, 2 = Signal, 3 = GND) | 5 V (4,8–7,2 V zulässig) | ~10 mA Ruhe / ~250–500 mA in Bewegung / Blockierstrom ~1,2–1,4 A (Datenblatt-Größenordnung, nachmessen) |

Im Schaltplan: C2 = 1000 µF Elko direkt am Stecker J1 (+5 V/GND) gegen
Anlaufeinbrüche. MG995 = Metallgetriebe, ca. 180° Stellbereich (nutzbar
~120–180°, Pulsbreite 1–2 ms je nach Exemplar), kein Winkelgeber nach
außen — Endanschläge per Software einmessen. **Nur echter Drehbereich,
keine Endlosdrehung** (außer die 360°-Variante des MG995).

GP1 gehört zu PWM-Slice 0 (mit GP0, dort PIO-UART DFPLAYER_RX — die
Nutzung von GP0 als UART kollidiert nicht mit PWM auf GP1). Die
3,3-V-Signalleitung genügt dem MG995 (Signal-High ab ~2,5–3 V).
Servo-Signal beim Start erst nach stabiler Rail aktivieren (kein
Zucken). Blockierstrom ~1,4 A + DFPlayer-Peak (bis ~0,9 A) + GPS/3.3V-Regler
liegen auf der 5V/3A-Logik-Rail (~0,3 A Reserve im Worst Case), siehe Offene Punkte.

### Mast (über dem Kopf)

| Sensor | Schnittstelle | Stecker | Versorgung | Strom |
| --- | --- | --- | --- | --- |
| WitMotion COIN-D6 LiDAR | UART → USB-Adapter → Jetson | Originalstecker des LiDAR + USB | 5 V vom Jetson | ~250–400 mA (Anlauf höher; prüfen) |

### Strom-Summen je Rail (aus den Tabellen oben)

| Rail | Verbraucher | Summe typ. – max. |
| --- | --- | --- |
| 3.3V extern (1A-Regler) | Mikrofon, Radar, Kompass, 2× Displays, PCF8574P, SW-420, Regensensor, LDR | ≈ 115–150 mA — weiterhin großzügig unter 1 A |
| 5V Logik (3A-Buck) | GPS, DFPlayer, Kopf-Servo MG995, Eingangsstrom des 3.3V-Reglers | ≈ 100–150 mA Ruhe … ≈ 2,2–2,7 A Peak bei blockiertem Servo + DFPlayer-Peak (DFPlayer bis ~0,9 A) — innerhalb der 3-A-Grenze (~0,3 A Reserve im Worst Case) |
| 5V Jetson-USB | Webcam, LiDAR | ≈ 400–700 mA (Anlauf LiDAR höher) — auf getrennte USB-Ports legen |

### Offene Punkte aus dem Steckbrief

- **Kopf-Kabelbaum (drehbar):** Kopf bündelt Mikrofon (5), Radar (5),
  GPS (3–4), Displays (7) = ~20–21 Leitungen + USB (Webcam). Drehbegrenzung,
  Kabelschleife einplanen; mit MG995 (~180°) ist kein Schleifring nötig,
  Kabel für ±90° Auslenkung ausreichend lang/flexibel dimensionieren.
  Antrieb: Kopf-Servo MG995 an GP1 (SERVO_HEAD), kein Winkelgeber.
- **Servo-Stromversorgung:** 5V-Buck unterstützt jetzt 3A → MG995 bleibt
  an der Logik-Rail (J1 an +5V). Worst Case (Servo blockiert ~1,4 A +
  DFPlayer-Peak bis ~0,9 A + GPS/3.3V-Regler ~0,3 A) ≈ 2,7 A, ~0,3 A
  Reserve (beides gleichzeitig unwahrscheinlich; Typwert < 0,5 A).
  Elko C2 (1000 µF) am J1 puffert Anlaufspitzen; Software: Bewegung rampen,
  Blockierung vermeiden. Buck-Modul mit echtem 3A-Dauerstrom (nicht nur
  Spitze) und Kühlung wählen.
- **GPS-Pegel:** Modul an 5 V, TX-Pegel des GY-NEO6MV2 ist 3,3 V (Chip-Pegel)
  → direkt an GP18 ok. GPS-RX ist nicht verdrahtet; nur nötig, falls das
  Modul konfiguriert werden soll.
- **LiDAR-Anlaufstrom** und gemeinsames Jetson-USB-Strombudget beim
  ersten Einschalten messen.
- **Schaltplan (Stand: Motor-Richtung am PCF8574P):** geprüft — EN an GP2/GP5, DIR an P2–P5, Vibration P0, BUSY P1, GP3/4/6/7 mit No-Connect, ADC_VREF-Kondensator C1, Foto-Teiler R6/R7, C3 am PCF8574P-VDD, Servo J1 mit C2 und `SERVO_HEAD` an GP1 stimmen mit diesem Dokument überein. **Noch nachzurüsten (Schaltplan):** Pull-ups 4,7–10 kΩ an P2–P5 und Pull-downs 10 kΩ an M_L_EN/M_R_EN.

## Allgemeine Hinweise für den Schaltplan

- Entkopplungskondensatoren (100nF) an jedem IC nah an dessen VDD/GND
  einplanen (PCF8574, GY-273, INMP441) — im Layout, nicht zwingend im
  Schaltplan-Netz sichtbar, aber als Bauteil einplanen.
- I2C-Pull-ups: ein Paar 4.7kΩ, SDA→3.3V und SCL→3.3V (**nicht** nach
  GND — das wäre ein Pull-*down* und würde den Bus lahmlegen), reicht für
  den ganzen Bus (4 Teilnehmer), sofern nicht schon auf einem der Module
  vorhanden.
- Gemeinsame Masse (GND) über alle drei Spannungsdomains (12V/5V/3.3V)
  sternförmig am Akku-Minuspol zusammenführen, um Ground-Loops zu
  vermeiden.

## Offene Punkte

- **XL6009-Boost-Modul für den Jetson reicht nicht.** Vorhandenes Modul
  (XL6009E1, TO-263, kein Kühlkörper) gegen die offizielle
  Jetson-Stromversorgung gerechnet: NVIDIA legt das Devkit auf 19V/3,42A
  (≈65W, deckt Jetson-Modul + Carrier-Board-Peripherie wie NVMe, Lüfter,
  USB-Geräte). Bei 11V-Eingang (3S-LiPo) und ~85% Wirkungsgrad braucht das
  volle 65W-Budget am Eingang ≈7A — der XL6009-Chip limitiert intern bei
  ~4A, ganz ohne Reserve für Lastspitzen (GPU-Inferenz-Bursts). Selbst nur
  für das Jetson-Modul allein (~25W) bleiben bei ~2,7A Eingangsstrom kaum
  Reserven, und ohne Kühlkörper auf dem Chip ist thermisches
  Abschalten/Drosseln im halbwegs geschlossenen Gehäuse realistisch — ein
  Spannungseinbruch am Jetson kann zu Brownout-Resets führen (Risiko für
  Dateisystem/SLAM-Stack während der Fahrt). Dazu kommt: 3S-LiPo sackt
  unter Last/gegen Ladeschluss auf ~9,9–10,5V, was das Verhältnis noch
  ungünstiger macht. **Ersatz nötig:** dediziertes 12V→19V-Boost-Modul mit
  ≥5A Dauerstrom-Rating und eigenem Kühlkörper/Lüfter (fertige Module für
  genau diesen "Jetson von Akku betreiben"-Zweck sind verfügbar), bevor
  der Jetson darüber betrieben wird.

- ~~3.3V-Regler-Marge (Pico-Onboard-Regler, VSYS→3V3)~~ — **gelöst,
  jetzt vollständig:** laut Pico-Datenblatt liefert der Onboard-Regler
  (RT6150B) max. ~300mA. Statt nur Displays/Radar auszulagern, hängt
  jetzt **die gesamte 3.3V-Peripherie** (GY-273, INMP441, PCF8574,
  Regen-/Vibrationssensor, 2× GC9A01, HLK-LD2402) an einem externen
  3.3V/1A-Standardregler von der 5V-Rail — der Pico-Onboard-Regler
  versorgt nur noch den RP2040-Chip selbst (~30–50mA, trivial). Der
  RP2040-Chip lässt sich nicht vom Onboard-Regler trennen, solange die
  native USB-Verbindung zum Jetson besteht (VBUS aktiviert VSYS
  zwangsläufig) — das ist aber unkritisch, da diese Last winzig ist. Der
  externe 1A-Regler hat mit ~110–180mA Worst-Case-Summe (Displays+Radar)
  plus ~106mA restliche Sensorik (~220–290mA gesamt) großzügig Reserve.

- **Farbsensoren (TCS3200, TCS34725) vorerst aus der Beschreibung
  entfernt.** Falls sie später wieder aufgenommen werden: TCS3200
  bräuchte wieder 5 Steuerleitungen (S0-S3, OE) — dafür reicht der eine
  PCF8574P (aktuell 6/8 Leitungen belegt) nicht mehr aus, ein zweiter
  Chip oder direkte RP2040-Pins (GP28) wären dann nötig.

- **WT588D durch DFPlayer Mini ersetzt.** Statt Parallel-/
  Kombinations-Tasten-Trigger jetzt UART-Steuerung (siehe eigener
  Abschnitt oben). Der PCF8574P hat dadurch keine Audio-Aufgabe mehr und
  ist auf Vibrationssensor und DFPlayer-BUSY umgewidmet — bleibt auf
  Default-Adresse 0x20, kein Adress-Jumper nötig (später kamen die
  Motor-Richtungsleitungen dazu, 2 von 8 Leitungen frei). Genaue Widerstandswerte für den
  DFPlayer-Spannungsteiler (aktuell 1kΩ/2kΩ als Richtwert) beim Aufbau
  mit einem Multimeter am tatsächlichen GP0-Pegel verifizieren.
