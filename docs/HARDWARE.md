# Hardware (optional) — the Amun Amulet & the Brain mode

**You never need any of this.** Amun's default and recommended input is the
microphone in your browser — zero hardware, fully offline. This page is for
people who want a physical build. Everything here is an *alternative* signal
source; if the device isn't found, Amun automatically falls back to the mic.

There are two optional paths:

1. **Amun Amulet** — a DIY breath controller (Arduino/ESP32 + sensor + display).
2. **Brain mode** — a NeuroSky MindWave headset (real EEG), bringing the original
   *Invisible-Driver* "control with your mind" idea back as a bonus.

---

## Bill of materials

| Component | Purpose | Approx. price |
|---|---|---|
| Arduino **Uno / Nano** or **ESP32** | reads the sensor, drives feedback, streams the signal | $4–9 |
| **Breath/wind sensor** — electret mic module *or* pressure/wind sensor on `A0` | turns breath into an analog value | $2–6 |
| **NeuroSky MindWave Mobile** *(Brain mode only)* | real EEG attention signal | ~$120 (AliExpress) |
| **OLED SSD1306 128×64** (I²C) | live breath bar + current command | ~$5 |
| **Bluetooth HC-05 / HM-10** | wireless serial link to the PC | ~$5 |
| **RGB LED + passive buzzer** | colour + sound feedback (climb/glide/dive) | ~$3 |
| Small **power bank** | run it untethered | — |

> The Amulet works over plain **USB serial** too — Bluetooth, the OLED, the LED
> and the buzzer are all optional niceties. Missing any of them is non-fatal.

---

## Path 1 — the Amun Amulet (breath)

Sketch: [`hardware/amun_amulet.ino`](../hardware/amun_amulet.ino). It samples the
sensor, smooths it (EMA), normalises to `0.000 … 1.000`, and prints one value per
line to **both** USB serial and the Bluetooth module. The PC reads those lines via
`SerialSource`.

### Wiring (Arduino Uno/Nano)

| Amulet part | Pin |
|---|---|
| Breath sensor analog out | `A0` |
| OLED SDA / SCL (I²C) | `A4` / `A5` (Uno) |
| RGB LED R / G / B (common cathode, via ~220Ω) | `9` / `10` / `11` (PWM) |
| Passive buzzer | `6` |
| HC-05 RX / TX | `2` / `3` (SoftwareSerial, **crossed**) |
| Power | 5V / GND (or power bank via USB) |

On ESP32 set `#define BOARD_ESP32 1`; it uses `Serial2` (GPIO16/17) for Bluetooth.

### Feedback

* **RGB LED** — deep blue = dive, gold = glide, teal/green = climb.
* **OLED** — title, current command, and a live breath bar with percentage.
* **Buzzer** — a soft tick while you climb hard; startup chime.

### Flash & run

```bash
# Arduino IDE: install "Adafruit SSD1306" + "Adafruit GFX", select your board, upload.
# Then on the PC (Linux example — bind the HC-05 to a serial port first):
amun --source serial --serial-port /dev/rfcomm0       # Bluetooth
amun --source serial --serial-port /dev/ttyUSB0       # USB cable
# Windows: --serial-port COM5     macOS: --serial-port /dev/cu.usbserial-XXXX
```

Needs the optional Python extra: `pip install "amun[serial]"` (pyserial). If it's
missing, or the port can't be opened, Amun prints a notice and **falls back to the
browser microphone**.

---

## Path 2 — Brain mode (NeuroSky MindWave)

The MindWave Mobile pairs over Bluetooth as a serial port and streams the
**ThinkGear** protocol. Amun decodes it with the pure-stdlib parser in
[`src/amun/thinkgear.py`](../src/amun/thinkgear.py) and uses the headset's
**attention** value (0–100) as the throttle — concentrate to climb, relax to dive.
No Arduino required for this path; the headset talks to the PC directly.

```bash
# pair the headset, bind it to a serial port, then:
amun --source neurosky --serial-port /dev/rfcomm0
```

This is the full-circle bonus: the original drove a car with brain waves; Amun can
do that **and** breath — so it's a superset of the idea, while still running for
everyone with just a microphone.

### Protocol notes

* Frame: `0xAA 0xAA  <plength>  <payload>  <checksum>`,
  `checksum = (~(sum(payload) & 0xFF)) & 0xFF`.
* Codes used: `0x02` poor-signal (contact quality), `0x04` attention, `0x05`
  meditation. Multi-byte rows (`≥0x80`, e.g. raw wave) are skipped cleanly.
* The parser resyncs after garbage and validates every checksum — see
  `tests/test_thinkgear.py` (runs with no hardware).

---

## Graceful degradation, always

```
serial / neurosky device present?  ──yes──▶  use it (OLED + LED + buzzer feedback)
            │
            no
            ▼
   browser microphone (default)   ◀── the game always works
```
