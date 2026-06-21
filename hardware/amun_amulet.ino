/*
 * ─────────────────────────────────────────────────────────────────────────────
 *  AMUN AMULET  ·  optional hardware companion for Amun (Breath–Computer Interface)
 * ─────────────────────────────────────────────────────────────────────────────
 *  A self-contained breath controller. Samples a breath/wind sensor, shows a live
 *  breath bar on an OLED, glows an RGB LED and chirps a buzzer for feedback, and
 *  streams a NORMALISED signal (0.000 .. 1.000, one value per line) to the PC over
 *  USB serial OR a Bluetooth (HC-05 / HM-10) link that appears as a serial port.
 *
 *  On the PC:   amun --source serial --serial-port /dev/rfcomm0
 *  No amulet?   Amun just uses the browser microphone. Hardware is a bonus.
 *
 *  Boards:  Arduino Uno / Nano (AVR) or ESP32.  Set BOARD_ESP32 below.
 *
 *  Bill of materials (see docs/HARDWARE.md): Arduino/ESP32, analog breath sensor
 *  (electret mic module or wind/pressure sensor) on A0, SSD1306 128x64 OLED (I2C),
 *  HC-05/HM-10 Bluetooth, common-cathode RGB LED, passive buzzer, small power bank.
 * ─────────────────────────────────────────────────────────────────────────────
 */

#include <Wire.h>
#include <Adafruit_GFX.h>
#include <Adafruit_SSD1306.h>

// ── configuration ────────────────────────────────────────────────────────────
#define BOARD_ESP32 0          // 1 for ESP32, 0 for Arduino Uno/Nano

#define SENSOR_PIN   A0        // breath sensor analog out
#define PIN_R        9         // RGB LED (common cathode) — PWM pins
#define PIN_G        10
#define PIN_B        11
#define BUZZER_PIN   6

#define OLED_W 128
#define OLED_H 64
#define OLED_ADDR 0x3C

// breath envelope tuning
const float ALPHA       = 0.30f;   // EMA smoothing
const float NOISE_FLOOR = 0.04f;   // fraction of full-scale that counts as silence
const float HARD_LEVEL  = 0.55f;   // fraction of full-scale that counts as a hard exhale
const float GLIDE_TH    = 0.30f;   // normalised level: dive vs glide
const float CLIMB_TH    = 0.66f;   // normalised level: glide vs climb

Adafruit_SSD1306 oled(OLED_W, OLED_H, &Wire, -1);

// Bluetooth serial: ESP32 uses Serial2; AVR uses SoftwareSerial on pins 2/3.
#if BOARD_ESP32
  #define BT Serial2
#else
  #include <SoftwareSerial.h>
  SoftwareSerial BT(2, 3);   // RX, TX  (cross to HC-05 TX, RX)
#endif

float envelope = 0.0f;

void setup() {
  Serial.begin(115200);
#if BOARD_ESP32
  BT.begin(115200, SERIAL_8N1, 16, 17);
#else
  BT.begin(9600);            // HC-05 default
#endif

  pinMode(PIN_R, OUTPUT); pinMode(PIN_G, OUTPUT); pinMode(PIN_B, OUTPUT);
  pinMode(BUZZER_PIN, OUTPUT);

  if (!oled.begin(SSD1306_SWITCHCAPVCC, OLED_ADDR)) {
    // OLED missing is non-fatal — the controller still streams its signal.
  } else {
    oled.clearDisplay();
    oled.setTextColor(SSD1306_WHITE);
    oled.setTextSize(2); oled.setCursor(8, 8);  oled.println("AMUN");
    oled.setTextSize(1); oled.setCursor(8, 34); oled.println("Breath Amulet");
    oled.setCursor(8, 46); oled.println("breathe to fly");
    oled.display();
  }
  chirp(1600, 60); delay(40); chirp(2200, 80);
}

void loop() {
  // 1. read sensor as a 0..1 fraction of full scale
  int raw = analogRead(SENSOR_PIN);
  float frac = raw / 1023.0f;

  // 2. smooth (exponential moving average)
  envelope = ALPHA * frac + (1.0f - ALPHA) * envelope;

  // 3. normalise to breath intensity using the calibration window
  float span = HARD_LEVEL - NOISE_FLOOR;
  float level = span > 0.0001f ? (envelope - NOISE_FLOOR) / span : 0.0f;
  level = constrain(level, 0.0f, 1.0f);

  // 4. stream to the PC (USB + Bluetooth), one value per line
  Serial.println(level, 3);
  BT.println(level, 3);

  // 5. local feedback: RGB + OLED + buzzer
  showLED(level);
  showOLED(level);
  if (level > CLIMB_TH) chirp(2400, 8);   // soft tick while climbing hard

  delay(16);   // ~60 Hz
}

// climb = teal/green, glide = gold, dive = deep blue
void showLED(float level) {
  int r, g, b;
  if (level < GLIDE_TH)      { r = 0;   g = 30;  b = 160; }   // dive
  else if (level < CLIMB_TH) { r = 245; g = 196; b = 30;  }   // glide
  else                       { r = 30;  g = 224; b = 200; }   // climb
  analogWrite(PIN_R, r); analogWrite(PIN_G, g); analogWrite(PIN_B, b);
}

void showOLED(float level) {
  oled.clearDisplay();
  oled.setTextSize(1);
  oled.setCursor(0, 0);
  oled.print("AMUN  ");
  oled.print(level < GLIDE_TH ? "DIVE " : level < CLIMB_TH ? "GLIDE" : "CLIMB");

  // breath bar
  int w = (int)(level * (OLED_W - 4));
  oled.drawRect(0, 18, OLED_W, 18, SSD1306_WHITE);
  oled.fillRect(2, 20, w, 14, SSD1306_WHITE);

  oled.setCursor(0, 44);
  oled.print("breath ");
  oled.print((int)(level * 100));
  oled.print("%");
  oled.display();
}

void chirp(int freq, int ms) {
  tone(BUZZER_PIN, freq, ms);
}
