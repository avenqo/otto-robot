# Otto — Bill of Materials

Status: `bestellt` (neu bestellt) · `vorhanden` (bereits im Bestand / vom Vorgängerbau übernehmbar) · `geplant` (noch zu beschaffen).

## Mechanik

Rein mechanische Teile ohne eigene Elektrik/Elektronik.

| Menge | Bauteil | Spezifikation | Preis | Status |
| --- | --- | --- | --- | --- |
| 2 | Rad | Ø 180mm, siehe [`20_hardware/3D/wheel.stl`](../3D/wheel.stl) | — | bestellt/gefertigt |
| 4 | Starre Flansch-Kupplung | 8mm Bohrung, Serie 3/3,17/4/5/6/7/8/10/11/12/14mm | 1,39€/Stk | bestellt |
| 4+ | Gewindeeinsatz (Heat-Set Insert) | M3, für Siebdruckplatte, Elektronik-Deck-Montage statt Heißkleber | — | geplant |
| 4+ | Abstandsbolzen | M3, Nylon, ~10-15mm, für Lötstellen-Clearance unter der Hauptplatine | — | geplant |
| n | Buchsenleiste (Sockel-Header) | 2,54mm-Raster, für steckbare Module (Pico, L298N, PCF8574, ...) statt Direktverlötung | — | geplant |
| 2 | Reihenklemme | Mehrpolig, Schraub- oder Federkontakt, Power-Hub (12V) + Logik-Verteiler (5V) | — | geplant |
| n | JST-PH-Sets (Buchse+Stecker, gecrimpt) | 2-/3-/4-/5-/6-polig, für alle Signal-/Datenverbindungen statt Dupont — siehe [`layout.md`](../layout.md#kabel-steckverbinder-tabelle) | — | geplant |
| n | JST-XH-Sets (Buchse+Stecker, gecrimpt) | Für die SPI-Verbindung zu den 2× GC9A01-Displays (Flachbandkabel) | — | geplant |
| 1 | Silikonlitze-Sortiment | 0,5–0,75mm² (Motorstrom) + 0,14–0,25mm² (Signal), flexibel für bewegten Aufbau | — | geplant |
| 1 | Verdrilltes Adernpaar (twisted pair) | Für Signalleitungen zum Mast (GPS, Regensensor) | — | geplant |

## Mechatronik

Antriebe — mechanische Bewegung mit direkt zugehöriger Elektrik.

| Menge | Bauteil | Spezifikation | Preis | Status |
| --- | --- | --- | --- | --- |
| 2 | DC-Getriebemotor | Zeng Whcd 5840-31ZY, Schneckengetriebe, 12V, 40RPM, Max. Torque 100kg | 21,79€/Stk | bestellt |

## Elektronik

Recheneinheiten, Treiber, Sensorik, Ein-/Ausgabe — siehe [`10_concepts/otto-concept.md`](../../10_concepts/otto-concept.md) für Pin-Zuordnung und Architektur.

| Menge | Bauteil | Spezifikation | Preis | Status |
| --- | --- | --- | --- | --- |
| 1 | Jetson Orin Nano | `brain`: Perception, Navigation, AI | — | geplant |
| 1 | Raspberry Pi Pico (RP2040) | `spine`: Echtzeit-Antrieb, Nahbereichssensorik | — | geplant |
| 1 | WitMotion COIN-D6 | dTOF-Lidar, 360°, 12m Reichweite, USB/UART 230400 Baud | — | geplant |
| 1 | USB-Webcam | Ersetzt ESP32-CAM, Bild für App & YOLO | — | geplant |
| 2 | L298N | Motortreiber, je 1 Board pro Motor, beide H-Brücken pro Board parallel gejumpert (~3-4A statt ~2A), Onboard-5V-Regler-Jumper entfernt — siehe [`motor-wiring.md`](../motor-wiring.md) | — | vorhanden |
| 1 | GY-273 | Kompass (HMC5883L), I2C0, auf dem Deck weit weg von Motoren/12V-Leitungen | — | vorhanden |
| 1 | GPS Neo-6M | GY-GPS6MV2, NMEA UART (RX only), separate Keramik-Antenne | — | vorhanden |
| 1 | HLK-LD2402 | Radar, Präsenzerkennung, PIO-UART | — | vorhanden |
| 1 | INMP441 | I2S-Mikrofon | — | vorhanden |
| 2 | GC9A01 | Rundes SPI-Display, 240×240 ("Augen") | — | vorhanden |
| 1 | Schalter | Ein-/Aus, Wippschalter | — | vorhanden |
| 1 | Taster | Reset-Taster (NO), zwischen Pico-RUN-Pin und GND, kein externer Pull-up nötig | — | geplant |
| 1 | V&A-Meter | Digitales Spannungs-/Strommessgerät, Diagnose auf dem Deck | — | vorhanden |
| 1 | Regensensor | MH-RD Raindrops-Modul, AO → GP26 (ADC0), DO unbeschaltet | — | vorhanden |
| 1 | Erschütterungssensor | Digital (SW-420-artig), via PCF8574, starr am Rahmen montiert | — | vorhanden |
| 1 | DFPlayer Mini | Sound-Modul (ersetzt WT588D), UART-gesteuert, MP3 von microSD, 5V betrieben | — | **fehlt** |
| 1 | microSD-Karte | Für DFPlayer Mini, Sound-Dateien als 0001.mp3, 0002.mp3, ... | — | **fehlt** |
| 1 | PCF8574P | I2C-Portexpander (8-bit), Default-Adresse 0x20, für Vibrationssensor (P0), DFPlayer-BUSY (P1) und L298N-Richtung (P2–P5), 6/8 Leitungen belegt | — | **fehlt** |
| 1 | Servo MG995 | Kopfdrehung, ~180°, Metallgetriebe, 5V, Blockierstrom ~1,4A, Signal GP1 (PWM 50 Hz), Stecker J1 (JST-XH 3) | — | geplant |
| 1 | Fotowiderstand (z. B. GL5528) | Helligkeit, Teiler mit 10kΩ (R7) → GP27 (ADC1), außen, JST-XH 2 | — | geplant |
| 1 | Widerstand 10kΩ | R7, Teiler für Fotowiderstand | — | geplant |
| 6 | Widerstand 4,7–10kΩ | Pull-ups an PCF8574P P2–P5 (L298N IN1/IN2, 4 Stück) plus Pull-downs an M_L_EN/M_R_EN (2 Stück, 10kΩ) | — | geplant |
| 2 | Elko 1000µF | C2 am Servo-Stecker J1 (5V), C3 am PCF8574P-VDD (3,3V) | — | geplant |
| 1 | Kondensator 220nF | C1, ADC_VREF nach GND | — | geplant |
| 1 | Lautsprecher | 4-8Ω, für DFPlayer Mini | — | **fehlt** |
| 1 | Widerstands-Set (1kΩ, 2kΩ) | Vorwiderstand + Spannungsteiler für DFPlayer-UART (5V-Modul an 3,3V-RP2040) | — | geplant |
| 1 | 12V→5V Buck-Konverter | ≥3A Dauerstrom, Logik-Rail (GPS, DFPlayer+Lautsprecher, Kopf-Servo MG995 **+ Eingangsstrom des externen 3,3V-Reglers**; Worst-Case ~2,7A bei blockiertem Servo + DFPlayer-Peak), getrennt vom L298N-Onboard-Regler | — | geplant |
| 1 | 3,3V/1A-Standardregler | Externe 3.3V-Rail für alle 3.3V-Peripherie außer dem RP2040-Chip (GY-273, INMP441, PCF8574P, Regen-/Vibrationssensor, Fotowiderstand-Teiler, 2× GC9A01, HLK-LD2402), von der 5V-Rail abgeleitet | — | geplant |
| 1 | 12V→19V Boost-Modul | ≥5A Dauerstrom, eigener Kühlkörper/Lüfter, für Jetson Orin Nano Devkit (19V/3,42A) — vorhandenes XL6009-Modul reicht nicht, siehe wiring-reference.md | — | geplant |
