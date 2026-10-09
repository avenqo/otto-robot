# Otto — Mechanischer Aufbau

2026-09-18

Ausgangspunkt: Vorgänger-Plattform (MDF-Deck auf Kettenfahrwerk, ESP32 + 2×
Motortreiber + LCD + Akku). Übernommen wird das Fahrwerk und die
grundsätzliche Deck-Bauweise. Nicht übernommen: die Servo-Schwenkkamera und
die Ultraschallsensoren. Der ESP32 wird durch den RP2040 (`spine`) ersetzt,
zusätzlich kommt der Jetson Orin Nano (`brain`) neu dazu. Komponentenliste
siehe [`20_hardware/components/BOM.md`](components/BOM.md), Pin-Zuordnung
siehe [`10_concepts/otto-concept.md`](../10_concepts/otto-concept.md).

## Grundprinzip: vier Zonen

```
        ┌───────────────────────┐
        │   Mast / Dach         │  GPS+Antenne, Regensensor, Lidar
        ├───────────────────────┤
        │   Front ("Gesicht")   │  2× GC9A01-Augen, Radar, Webcam, Lautsprecher
        ├───────────────────────┤
        │   Elektronik-Deck     │  RP2040, Jetson, L298N×2, Spannungswandler,
        │                       │  I2C-Expander, Kompass, Kopf-Servo, Akku
        ├───────────────────────┤
        │   Unterbau / Bug      │  Motoren, Fahrwerk, Farbsensoren (nach unten),
        │                       │  Vibrationssensor (starr am Rahmen)
        └───────────────────────┘
```

Leitgedanke: schwer und tief (Akku, Motoren) unten für einen niedrigen
Schwerpunkt; alles, was freie Sicht/Feld braucht (GPS-Himmelsblick,
Regentropfen, Lidar-Rundumsicht) möglichst hoch und frei von Verdeckung;
alles Störungsempfindliche (Kompass, Mikrofon) mit Abstand zu Motoren,
Kabeln und Vibrationsquellen.

## Unterbau / Bug

- Fahrwerk, Motoren (2× 5840-31ZY), Räder

## Elektronik-Deck

Entspricht der Position des alten MDF-Boards, gleiche Befestigungspunkte
nutzbar.

- **RP2040 (`spine`):** zentral, dort wo vorher der ESP32 saß — kürzeste
  Wege zu den beiden L298N-Modulen links/rechts davon (wie beim Vorgänger).
- **2× L298N:** links/rechts vom RP2040, wie im Vorgängeraufbau.
- **Vibrationssensor:** starr (nicht gedämpft!) direkt am Fahrwerksrahmen
  verschraubt — er soll genau die mechanischen Stöße des Chassis spüren,
  keine Dämpfung dazwischen.
- **Jetson Orin Nano (`brain`):** eigener Platz auf dem Deck mit Freiraum
  für den Lüfter (siehe Lüfter/Servo-Halterung im alten Foto, Position
  wiederverwendbar) — Jetson braucht aktive Kühlung und sollte nicht direkt
  über dem Akku sitzen (Wärme).
- **Spannungswandler/Buck-Converter, Sicherung, Ein/Aus-Schalter,
  Spannungsanzeige:** wie beim Vorgänger auf einer kleinen Lochraster-/
  Stripboard-Fläche, gut zugänglich für Diagnose.
- **PCF8574P-Expander (0x20):** nur noch einer (Farbsensoren entfernt) —
  seit dem Wechsel von WT588D auf den UART-gesteuerten DFPlayer Mini
  jetzt für Vibrationssensor (P0), DFPlayer-BUSY (P1) und die vier
  L298N-Richtungsleitungen (P2–P5) zuständig, kann zentral auf dem Deck
  bleiben (nahe der L298N, aber I2C-Kabel weg von Motorleitungen). Regensensor (AO → GP26) und Fotowiderstand
  (→ GP27) hängen direkt am RP2040-ADC.
- **GY-273/HMC5883L Kompass:** auf dem Deck, **so weit wie möglich von
  Motoren, L298N-Boards, Akku und dicken 12V-Leitungen entfernt** (Ecke
  des Decks, plan ausgerichtet). Kalibrierung (Hard-/Soft-Iron) am
  fertigen Aufbau mit laufenden Motoren.
- **Kopf-Servo MG995 (Drehung des Kopfes):** auf dem Deck, Signal GP1
  (SERVO_HEAD), 5V über J1 (JST-XH 3) mit 1000µF-Elko am Stecker.
  Stellbereich ~180°, Kabel zum Kopf mit Schleife für ±90°. Logik-Buck liefert 3A
  (Blockierstrom ~1,4 A eingerechnet), siehe `wiring-reference.md`.
- **DFPlayer Mini + microSD-Karte:** auf dem Deck, SD-Karte zugänglich
  montieren (seitlich am Deckrand oder mit kleiner Aussparung im
  Gehäuse), damit Sound-Dateien ohne Zerlegen des Roboters
  ausgetauscht/aktualisiert werden können.
- **INMP441-Mikrofon:** auf dem Deck, aber schwingungsentkoppelt (kleine
  Gummi-/Schaumstoff-Puffer) und mit Abstand zu den Motoren — Motorvibration
  und -geräusch koppeln sonst direkt ins Signal ein.
- **Akku (LiPo, wie im Vorgänger mit XT60):** tief und mittig für tiefen
  Schwerpunkt, per Klettband gesichert wie bisher.


## Front ("Gesicht")

- **2× GC9A01 (Augen):** vorne, symmetrisch links/rechts auf Kopf-/Gesichts-
  höhe montiert — das ist der primäre Blickfang für Betrachter, sollte klar
  sichtbar und nicht durch den Lidar-Mast verdeckt sein.
- **HLK-LD2402 Radar:** vorne, in Fahrtrichtung, auf Stoßstangenhöhe.
  Wichtig: Radar sieht nicht durch Metall — Gehäuseausschnitt an der Stelle
  muss aus Kunststoff/nicht-leitendem Material sein.
- **USB-Webcam:** fest (keine Schwenkmechanik mehr), vorne erhöht montiert,
  leicht nach unten geneigt, damit sowohl der Weg vor dem Roboter als auch
  YOLO-Objekte im Nahbereich erfasst werden.
- **Lautsprecher (DFPlayer Mini):** an der Front, Schallaustritt nach
  vorne/oben, Platzierung unkritisch (DFPlayer-Modul selbst sitzt auf
  dem Elektronik-Deck, siehe oben).

## Mast / Dach

Hier sitzen die Komponenten, die entweder freie Sicht nach oben brauchen
oder möglichst weit weg von Motoren/Kabeln/Metall müssen. Ein erhöhter
Mast oder eine Dachplatte auf Standoffs über dem Elektronik-Deck bietet
sich an.

- **Lidar (WitMotion COIN-D6):** höchster Punkt des Roboters, zentral, so
  dass die 360°-Drehebene von nichts anderem (Mast-Antenne, Regensensor-
  Halterung) geschnitten wird. Alles andere auf dem Dach muss niedriger
  sitzen als die Lidar-Scanebene oder außerhalb ihres Radius.
- **GPS-Modul + Keramik-Antenne:** so hoch wie möglich, freier Himmelsblick,
  Antenne nach oben, mit Abstand zu Motorkabeln/Akku (EMI). Antenne separat
  vom Board positionierbar (per U.FL-Kabel) — Board kann tiefer sitzen,
  nur die Antenne muss oben frei liegen.
- **Regensensor:** ganz oben, horizontal mit leichter Neigung (damit
  Tropfen ablaufen und nicht stehen bleiben), an der höchsten unverdeckten
  Stelle — sonst verzögerte/verfälschte Erkennung.

## Verkabelung

Alle Komponenten werden einzeln auf der Siebdruckplatte verschraubt (siehe
Montage-Diskussion oben), nicht auf einer gemeinsamen Platine — die
Verbindungen zwischen ihnen laufen also über Kabel. Drei Kategorien mit
unterschiedlichen Anforderungen:

- **Motorstrom** (Akku → L298N, L298N → Motor): 0,5–0,75mm² Litze,
  Schraubklemmen oder XT30-Stecker. Keine Dupont-/Jumperkabel — nicht für
  die Stromstärke ausgelegt und lösen sich durch Vibration.
- **Logik-Versorgung** (5V/3,3V + GND): sternförmig von einer zentralen
  Reihenklemme hinter dem Spannungswandler zu jedem Modul einzeln — fällt
  ein Modul aus/wird abgeklemmt, bleiben die anderen versorgt.
- **Signal/Daten**: durchgängig **JST-PH oder JST-XH** statt Dupont, da
  rastend und vibrationsfest. Der I2C-Bus braucht einen kleinen **Hub**
  (Stripboard mit SDA/SCL/VCC/GND-Schiene und mehreren parallelen
  JST-PH-Buchsen), da die meisten Breakout-Boards nur einen Header ohne
  Durchgang haben.

Wichtig: Motorkabel (PWM-Schaltrauschen) nicht mit I2C-/Kompass-/
Mikrofon-Leitungen im selben Kabelbaum bündeln — getrennt verlegen, sonst
Störeinkopplung auf die empfindlichen Signale. Bei den langen Strecken zum
Mast (GPS, Regensensor) verdrilltes Adernpaar für die Signalleitungen verwenden.

### Kabel-/Steckverbinder-Tabelle

| Von | Nach | Signale | Adern | Stecker | Kabel/Hinweis |
| --- | --- | --- | --- | --- | --- |
| Akku (XT60) | Schalter → Sicherung → Reihenklemme (Power-Hub) | 12V, GND | 2 | XT60 → Schraubklemme | 0,75mm², kurz |
| Reihenklemme (12V) | L298N links | 12V, GND | 2 | Schraubklemme | 0,5–0,75mm² |
| Reihenklemme (12V) | L298N rechts | 12V, GND | 2 | Schraubklemme | 0,5–0,75mm² |
| Reihenklemme (12V) | DC/DC-Wandler (Eingang) | 12V, GND | 2 | Schraubklemme | 0,5mm² |
| DC/DC-Wandler (5V-Ausgang) | Logik-Verteiler (2. Reihenklemme) | 5V, GND | 2 | Schraubklemme | 0,5mm² |
| Logik-Verteiler | Pico (VSYS/GND), je Sensor/Display einzeln | 5V, GND | 2 je Abzweig | JST-PH 2-pol | sternförmig, nicht durchschleifen |
| L298N links | Motor links | Motor+, Motor− | 2 | Schraubklemme | 0,5–0,75mm² |
| L298N rechts | Motor rechts | Motor+, Motor− | 2 | Schraubklemme | 0,5–0,75mm² |
| Pico (GP2) + PCF8574P (P2, P3) | L298N links | EN(PWM), IN1, IN2 | 3 | JST-PH 3-pol | kurz, Deck-intern; 4,7–10k Pull-up an IN1/IN2, 10k Pull-down an EN |
| Pico (GP5) + PCF8574P (P4, P5) | L298N rechts | EN(PWM), IN1, IN2 | 3 | JST-PH 3-pol | kurz, Deck-intern; wie links |
| Pico (GP8/GP9) | I2C-Hub | SDA, SCL, VCC, GND | 4 | JST-PH 4-pol | Hub direkt neben Pico |
| I2C-Hub | GY-273 (Kompass) | SDA, SCL, VCC, GND | 4 | JST-PH 4-pol | Deck-intern, weit weg von Motoren/12V-Leitungen |
| I2C-Hub | PCF8574 (0x20) | SDA, SCL, VCC, GND | 4 | JST-PH 4-pol | Deck-intern |
| Pico (GP10–GP14) | GC9A01 Display 1 | SCK, MOSI, DC, CS1, VCC, GND (7-Pin-Modul, kein BLK, RST fest 3,3V) | 6 | Flachbandkabel + JST-XH | zur Front |
| Pico (GP10, GP11, GP12, GP13) geteilt | GC9A01 Display 2 | SCK, MOSI, DC, CS2 (gemeinsam VCC/GND) | — | Flachbandkabel + JST-XH | SCK/MOSI/DC von Display 1 durchgeschleift, nur CS2 separat |
| Pico (GP15–GP17) | INMP441 | BCLK, WS, SD, VCC, GND | 5 | JST-PH 5-pol | schwingungsentkoppelt, abseits Motorkabel |
| Pico (GP18) | GPS Neo-6M | RX (Pico) ← TX (GPS), VCC, GND | 3 | JST-PH 3-pol | zum Mast, verdrillt |
| Pico (GP19/GP20) | HLK-LD2402 Radar | TX, RX, VCC, GND | 4 | JST-PH 4-pol | zur Front |
| Pico (GP22) | HLK-LD2402 IO | Presence-Signal | 1 | JST-PH (Ader im Radar-Kabel) | zur Front, siehe Radar-Zeile oben |
| Pico (GP26) | Regensensor | AO (analog), VCC, GND | 3 | JST-PH 3-pol | zum Mast, verdrillt; DO unbeschaltet |
| Pico (GP27) | Fotowiderstand (LDR) | Teilerpunkt PHOTO_R, 3,3V, GND | 2–3 | JST-XH 2 | außen; R7 (10k) auf Platine |
| Pico (GP1) | Kopf-Servo MG995 | SERVO_HEAD (PWM), +5V, GND | 3 | JST-XH 3 (J1) | Deck, Elko 1000µF am Stecker, 5V aus 3A-Logik-Buck |
| PCF8574P (P0) | Erschütterungssensor | Signal (DO), VCC, GND | 3 | JST-PH 3-pol | Deck-intern |
| PCF8574P (P1) | DFPlayer BUSY | BUSY | 1 | JST-PH (Ader im Audio-Kabel) | Deck-intern |
| Pico (GP21) | DFPlayer Mini RX | TX (Pico) → RX (Modul), über 1kΩ-Vorwiderstand | 1 | JST-PH (Ader im Audio-Kabel) | Deck-intern |
| Pico (GP0) | DFPlayer Mini TX | RX (Pico) ← TX (Modul), über Spannungsteiler 1k/2kΩ | 1 | JST-PH (Ader im Audio-Kabel) | Deck-intern |
| DFPlayer Mini | Lautsprecher | Speaker+, Speaker− | 2 | Schraubklemme oder JST | Front, kein Bus |
| DFPlayer Mini | microSD-Karte | — | — | microSD-Slot (onboard) | zugänglich montieren, siehe Elektronik-Deck oben |
| Pico (USB) | Jetson Orin Nano | USB-CDC (V,/T,-Protokoll) | — | USB-Kabel | siehe README.md |

Adernzahlen/Pin-Namen sind der aktuelle Planungsstand aus
[`Config.h`](../30_spine/spine/Config.h) — bei Änderungen an der Pin-Belegung
dort zuerst nachziehen, dann diese Tabelle.

## Offene Punkte

- Exakte Mast-Geometrie (Höhe, Materialstärke) hängt vom 3D-Druck-Design ab
  — noch kein STL für Dach/Mast vorhanden (nur `wheel.stl` bisher).
  Größe/Gewicht von Jetson + Kühlkörper/Lüfter noch nicht vermessen.
- Kompass (jetzt auf dem Deck): Kalibrierung (Hard-/Soft-Iron) sollte am fertigen Aufbau erfolgen,
  nicht isoliert auf der Werkbank — Abstand zu Metallteilen erst dann final
  verifizierbar.
- Kabellängen für die Mast-Strecke (GPS, Regensensor) noch nicht
  vermessen — hängt von der finalen Mast-Höhe ab; Durchführungen im Chassis
  für diese Kabel einplanen.
- I2C-Hub (Stripboard mit JST-PH-Buchsen) noch nicht gebaut/dimensioniert.
