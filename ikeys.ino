/*
 * MIT License
 *
 * Copyright (c) 2026 controllercustom@myyahoo.com
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all
 * copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 */

#include <WiFiManager.h>
#include <ArduinoOTA.h>
#include <ESPmDNS.h>
#include <WebServer.h>
#include <WebSocketsServer.h>
#include <Preferences.h>
#include "USB.h"
#include <USBHIDKeyboard.h>
#include <USBHIDMouse.h>
#include <USBHIDConsumerControl.h>
#ifdef ARDUINO_M5STACK_ATOMS3
#include <M5GFX.h>
#endif
#include <esp_wifi.h>

#define VERSION "1.0.4"

// Timing instrumentation — uncomment #define TIMING below for latency measurement
// #define TIMING
#ifdef TIMING
#include <esp_timer.h>
static uint64_t _t_ws = 0;
static uint64_t _t_hid = 0;
static char _t_type = 'K';
static bool _t_pending = false;
#define TIMING_STAMP_WS()      do { _t_ws = esp_timer_get_time(); _t_hid = 0; _t_pending = true; } while(0)
#define TIMING_STAMP_HID(t)    do { if (_t_pending && !_t_hid) { _t_hid = esp_timer_get_time(); _t_type = (t); } } while(0)
#define TIMING_PRINT()         do { if (_t_pending && _t_hid) { Serial.printf("[TIMING] %c ws=%llu hid=%llu fw_us=%llu\n", _t_type, _t_ws, _t_hid, _t_hid - _t_ws); _t_pending = false; _t_hid = 0; } } while(0)
#else
#define TIMING_STAMP_WS()
#define TIMING_STAMP_HID(t)
#define TIMING_PRINT()
#endif

volatile uint8_t ledState = 0;
volatile uint8_t ledStateChanged = 0;

USBHIDKeyboard keyboard;
USBHIDRelativeMouse mouse;
USBHIDConsumerControl consumer;
#ifdef ARDUINO_M5STACK_ATOMS3
M5GFX display;
#endif
WebServer server(80);
WebSocketsServer webSocket(81);

// ====================================================================
// Raw HID keycode constants (USB HID Usage Tables, Keyboard/Keypad page 0x07)
// The built-in USBHIDKeyboard uses Arduino-style keycodes (0x80+/0x88+),
// but iKeys sends raw HID usage IDs via pressRaw/releaseRaw, so we need
// the raw HID values here, NOT the Arduino-style defines from the header.
// ====================================================================
#define KEY_UP        0x52
#define KEY_DOWN      0x51
#define KEY_LEFT      0x50
#define KEY_RIGHT     0x4F
#define KEY_DELETE    0x4C
#define KEY_HOME      0x4A
#define KEY_END       0x4D
#define KEY_PAGE_UP   0x4B
#define KEY_PAGE_DOWN 0x4E
#define KEY_INSERT    0x49
#define KEY_TAB       0x2B
#define KEY_CAPS_LOCK 0x39
#define KEY_NUM_LOCK  0x53
#define KEY_SPACE     0x2C
#define KEY_F1        0x3A

#define KEY_NP_DIV    0x54
#define KEY_NP_MUL    0x55
#define KEY_NP_SUB    0x56
#define KEY_NP_ADD    0x57
#define KEY_NP_ENT    0x58
#define KEY_NP1       0x59
#define KEY_NP2       0x5A
#define KEY_NP3       0x5B
#define KEY_NP4       0x5C
#define KEY_NP5       0x5D
#define KEY_NP6       0x5E
#define KEY_NP7       0x5F
#define KEY_NP8       0x60
#define KEY_NP9       0x61
#define KEY_NP0       0x62
#define KEY_NP_DOT    0x63

// Consumer control codes (from USB HID Consumer page)
#define MEDIA_MUTE   0x00E2
#define MEDIA_VOL_DN 0x00EA
#define MEDIA_VOL_UP 0x00E9
#define MEDIA_PLAY   0x00CD
#define MEDIA_PREV   0x00B6
#define MEDIA_NEXT   0x00B5
#define MEDIA_FF     0x00B3
#define MEDIA_RW     0x00B4

// Modifier bit positions (USB HID boot keyboard report modifier byte)
#define MOD_LSHIFT 0x02

// ====================================================================
// Direction masks (iKeys-specific movement, not HID button masks)
// ====================================================================
#define DIR_LEFT   0x01
#define DIR_RIGHT  0x02
#define DIR_UP     0x04
#define DIR_DOWN   0x08

// ====================================================================
// State
// ====================================================================
uint8_t shiftRefCount = 0;
uint8_t ctrlRefCount = 0;
uint8_t altRefCount = 0;
uint8_t guiRefCount = 0;

uint8_t mouseDirections = 0;
bool leftButtonLocked = false;
bool smartTypingEnabled = false;
bool smartTypingShiftNext = false;
bool macOSMode = false;
uint8_t mouseSpeed = 5;
uint8_t mouseAccel = 0;
#define MAX_WS_CLIENTS 10
bool numpadMode[MAX_WS_CLIENTS] = {false};
bool mouseMoving = false;
unsigned long mouseMoveStartTime = 0;
unsigned long lastMouseMove = 0;
const unsigned long MOUSE_TICK_MS = 20;

char hostname[33];
bool portalConfigSaved = false;
WiFiManagerParameter customHostnameParam("hostname", "Device hostname", "ikeys", 32);

#ifdef ARDUINO_M5STACK_ATOMS3
#define RESET_BUTTON_PIN 41
#else
#define RESET_BUTTON_PIN 0
#endif
unsigned long resetPressStart = 0;
bool resetButtonWasLow = false;
unsigned long lastWSActivity = 0;
int wsClientCount = 0;

enum DClickState { DC_IDLE, DC_DOWN1, DC_UP1, DC_DOWN2, DC_UP2 };
DClickState dclickState = DC_IDLE;
unsigned long dclickTimer = 0;

// ====================================================================
// charToHID — ASCII to HID keycode (PROGMEM table, indices 0..127)
// ====================================================================
static uint8_t charToHID(char c) {
  if ((uint8_t)c > 127) return 0;
  static const uint8_t PROGMEM table[128] = {
    0,0,0,0,0,0,0,0, 0x2A,0x2B,0x28,0,0,0x28,0,0,
    0,0,0,0,0,0,0,0, 0,0,0,0x29,0,0,0,0,
    0x2C,0x1E,0x34,0x20, 0x21,0x22,0x24,0x34,
    0x26,0x27,0x25,0x2E, 0x36,0x2D,0x37,0x38,
    0x27,0x1E,0x1F,0x20, 0x21,0x22,0x23,0x24,
    0x25,0x26,0x33,0x33, 0x36,0x2E,0x37,0x38,
    0x1F,0x04,0x05,0x06, 0x07,0x08,0x09,0x0A,
    0x0B,0x0C,0x0D,0x0E, 0x0F,0x10,0x11,0x12,
    0x13,0x14,0x15,0x16, 0x17,0x18,0x19,0x1A,
    0x1B,0x1C,0x1D,0x2F, 0x31,0x30,0x23,0x2D,
    0x35,0x04,0x05,0x06, 0x07,0x08,0x09,0x0A,
    0x0B,0x0C,0x0D,0x0E, 0x0F,0x10,0x11,0x12,
    0x13,0x14,0x15,0x16, 0x17,0x18,0x19,0x1A,
    0x1B,0x1C,0x1D,0x2F, 0x31,0x30,0x35,0
  };
  return pgm_read_byte(&table[(uint8_t)c]);
}

// ====================================================================
// needsShift — returns true if a printable ASCII character requires
//              the Shift modifier (PROGMEM table, indices 0..127)
// ====================================================================
static bool needsShift(char c) {
  static const bool PROGMEM table[128] = {
    0,0,0,0,0,0,0,0, 0,0,0,0,0,0,0,0,
    0,0,0,0,0,0,0,0, 0,0,0,0,0,0,0,0,
    0,1,1,1,1,1,1,0, 1,1,1,1,0,0,0,0,
    0,0,0,0,0,0,0,0, 0,0,1,0,1,0,1,1,
    1,1,1,1,1,1,1,1, 1,1,1,1,1,1,1,1,
    1,1,1,1,1,1,1,1, 1,1,1,0,0,0,1,1,
    0,0,0,0,0,0,0,0, 0,0,0,0,0,0,0,0,
    0,0,0,0,0,0,0,0, 0,0,0,1,1,1,1,0
  };
  return ((uint8_t)c) < 128 && pgm_read_byte(&table[(uint8_t)c]);
}

// ====================================================================
// Custom keyboard state tracking (replaces ESP32USBHID internal state)
// ====================================================================
uint8_t kbdModifiers = 0;
uint8_t kbdKeys[6] = {0};
int kbdKeyCount = 0;
uint8_t keyCustomRefCount[256] = {0};
uint16_t currentConsumerUsage = 0;

static void sendKbdReport() {
  TIMING_STAMP_HID('K');
  KeyReport report;
  report.modifiers = kbdModifiers;
  report.reserved = 0;
  memset(report.keys, 0, 6);
  for (int i = 0; i < kbdKeyCount; i++) {
    report.keys[i] = kbdKeys[i];
  }
  keyboard.sendReport(&report);
}

static void pressKeyCustom(uint8_t kc) {
  if (kc == 0) return;
  if (keyCustomRefCount[kc] == 0) {
    bool already = false;
    for (int i = 0; i < kbdKeyCount; i++) {
      if (kbdKeys[i] == kc) { already = true; break; }
    }
    if (!already && kbdKeyCount < 6) {
      kbdKeys[kbdKeyCount++] = kc;
    }
  }
  if (keyCustomRefCount[kc] < 255) keyCustomRefCount[kc]++;
  sendKbdReport();
}

static void releaseKeyCustom(uint8_t kc) {
  if (kc == 0) return;
  if (keyCustomRefCount[kc] > 0) keyCustomRefCount[kc]--;
  if (keyCustomRefCount[kc] > 0) return;
  for (int i = 0; i < kbdKeyCount; i++) {
    if (kbdKeys[i] == kc) {
      kbdKeys[i] = kbdKeys[--kbdKeyCount];
      kbdKeys[kbdKeyCount] = 0;
      break;
    }
  }
  sendKbdReport();
}

static void releaseAllCustom() {
  kbdModifiers = 0;
  memset(kbdKeys, 0, 6);
  kbdKeyCount = 0;
  sendKbdReport();
}

static void pressModCustom(uint8_t mod) {
  kbdModifiers |= mod;
  sendKbdReport();
}

static void releaseModCustom(uint8_t mod) {
  kbdModifiers &= ~mod;
  sendKbdReport();
}

// ====================================================================
// HID Helpers
// ====================================================================
static void sendKeycode(uint8_t kc) {
  pressKeyCustom(kc);
  delay(1);
  releaseKeyCustom(kc);
}

static void pressHeldKey(uint8_t kc) {
  pressKeyCustom(kc);
}

static void releaseHeldKey(uint8_t kc) {
  releaseKeyCustom(kc);
}

static void mouseDoubleClick() {
  if (dclickState == DC_IDLE) {
    dclickState = DC_DOWN1;
    TIMING_STAMP_HID('M'); mouse.press(MOUSE_LEFT);
    dclickTimer = millis();
  }
}

static void toggleLeftLock() {
  leftButtonLocked = !leftButtonLocked;
  if (leftButtonLocked) {
    TIMING_STAMP_HID('M'); mouse.press(MOUSE_LEFT);
  } else {
    TIMING_STAMP_HID('M'); mouse.release(MOUSE_LEFT);
  }
  if (wsClientCount > 0) {
    webSocket.broadcastTXT(leftButtonLocked ? "#DRAG:1" : "#DRAG:0");
  }
}

static void resetState() {
  releaseAllCustom();
  memset(keyCustomRefCount, 0, sizeof(keyCustomRefCount));
  mouse.release(MOUSE_LEFT | MOUSE_RIGHT);
  consumer.release();
  currentConsumerUsage = 0;
  shiftRefCount = ctrlRefCount = altRefCount = guiRefCount = 0;
  mouseDirections = 0;
  mouseMoving = false;
  mouseMoveStartTime = 0;
  leftButtonLocked = false;
  smartTypingShiftNext = false;
}

// ====================================================================
// Key Handlers
// ====================================================================
static void handleSingleChar(const char* key) {
  if (!key[0] || key[1]) return;
  char c = key[0];
  uint8_t kc = charToHID(c);
  if (kc == 0) return;
  uint8_t savedMod = kbdModifiers;
  bool doCaps = smartTypingShiftNext && ((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z'));
  if (needsShift(c) || doCaps) kbdModifiers |= 0x02;
  if (doCaps) smartTypingShiftNext = false;
  pressKeyCustom(kc);
  kbdModifiers = savedMod;

  if (smartTypingEnabled) {
    if (c == 'q' || c == 'Q') {
      sendKeycode(charToHID('u'));
    } else if (c == '.' || c == '!' || c == '?') {
      sendKeycode(0x2C);
      sendKeycode(0x2C);
      smartTypingShiftNext = true;
    }
  }
}

static uint8_t numpadKeycode(const char* key) {
  switch (key[3]) {
    case '0': return KEY_NP0;
    case '1': return KEY_NP1;
    case '2': return KEY_NP2;
    case '3': return KEY_NP3;
    case '4': return KEY_NP4;
    case '5': return KEY_NP5;
    case '6': return KEY_NP6;
    case '7': return KEY_NP7;
    case '8': return KEY_NP8;
    case '9': return KEY_NP9;
    case 'D': return KEY_NP_DOT;
    case 'E': if (key[4] == 'n') return KEY_NP_ENT; break;
    case '+': return KEY_NP_ADD;
    case '-': return KEY_NP_SUB;
    case '*': return KEY_NP_MUL;
    case '/': return KEY_NP_DIV; break;
  }
  return 0;
}

static void handleNumpadKey(const char* key) {
  uint8_t kc = numpadKeycode(key);
  if (kc) pressHeldKey(kc);
}

static void releaseNumpadKey(const char* key) {
  uint8_t kc = numpadKeycode(key);
  if (kc) releaseHeldKey(kc);
}

static void handleMediaKey(const char* key) {
  uint16_t usage = 0;
       if (strcmp(key, "*MEDmute")   == 0) usage = MEDIA_MUTE;
  else if (strcmp(key, "*MEDvoldn")  == 0) usage = MEDIA_VOL_DN;
  else if (strcmp(key, "*MEDvolup")  == 0) usage = MEDIA_VOL_UP;
  else if (strcmp(key, "*MEDplay")   == 0) usage = MEDIA_PLAY;
  else if (strcmp(key, "*MEDprev")   == 0) usage = MEDIA_PREV;
  else if (strcmp(key, "*MEDnext")   == 0) usage = MEDIA_NEXT;
  else if (strcmp(key, "*MEDff")     == 0) usage = MEDIA_FF;
  else if (strcmp(key, "*MEDrw")     == 0) usage = MEDIA_RW;
  if (usage) { currentConsumerUsage = usage; TIMING_STAMP_HID('C'); consumer.press(usage); }
}

void handleKeyDown(const char* key) {
  if (key[0] != '*') {
    handleSingleChar(key);
    return;
  }
  if (strncmp(key, "*MED", 4) == 0) { handleMediaKey(key); return; }
  if (strncmp(key, "*Mac", 4) == 0) {
    macOSMode = !macOSMode;
    { Preferences p; p.begin("ikeys", false); p.putUChar("macmode", macOSMode); p.end(); }
    webSocket.broadcastTXT(macOSMode ? "#MAC:1" : "#MAC:0");
    return;
  }
  switch (key[1]) {
    case 'M':
      switch (key[2]) {
        case 'U':
          if (key[3] == 'L') { mouseDirections |= DIR_UP | DIR_LEFT; }
          else if (key[3] == 'p') { mouseDirections |= DIR_UP; }
          else { mouseDirections |= DIR_UP | DIR_RIGHT; }
          return;
        case 'D':
          if (key[3] == 'L') { mouseDirections |= DIR_DOWN | DIR_LEFT; }
          else if (key[3] == 'n') { mouseDirections |= DIR_DOWN; }
          else { mouseDirections |= DIR_DOWN | DIR_RIGHT; }
          return;
        case 'L': mouseDirections |= DIR_LEFT; return;
        case 'R': mouseDirections |= DIR_RIGHT; return;
      }
      return;
    case 'U':
      if (key[2] == 'p' && key[3]) { pressHeldKey(KEY_UP); }
      return;
    case 'D':
      if (key[2] == 'n' && key[3]) { pressHeldKey(KEY_DOWN); }
      else if (key[2] == 'e') { pressHeldKey(KEY_DELETE); }
      return;
    case 'L':
      if (key[2] == 'C') { TIMING_STAMP_HID('M'); mouse.press(MOUSE_RIGHT); }
      else if (key[2] == 'f') { pressHeldKey(KEY_LEFT); }
      return;
    case 'R':
      if (key[2] == 'C') { toggleLeftLock(); }
      else if (key[2] == 'g') { pressHeldKey(KEY_RIGHT); }
      return;
    case 'S':
      if (key[2] == 'h') {
        if (shiftRefCount == 0) pressModCustom(0x02);
        if (shiftRefCount < 255) shiftRefCount++;
      } else if (key[2] == 'm') { smartTypingEnabled = !smartTypingEnabled; { Preferences p; p.begin("ikeys", false); p.putUChar("smarten", smartTypingEnabled); p.end(); } webSocket.broadcastTXT(smartTypingEnabled ? "#SMT:1" : "#SMT:0"); }
      else if (key[2] == 'H') pressHeldKey(KEY_TAB);
      else mouseDoubleClick();
      return;
    case 'C':
      if (key[2] == 'n') { TIMING_STAMP_HID('M'); mouse.press(MOUSE_LEFT); }
      else if (key[2] == 'a') pressHeldKey(KEY_CAPS_LOCK);
      else if (key[2] == 't') {
        if (ctrlRefCount == 0) pressModCustom(0x01);
        if (ctrlRefCount < 255) ctrlRefCount++;
      } else {
        if (guiRefCount == 0) pressModCustom(0x08);
        if (guiRefCount < 255) guiRefCount++;
      }
      return;
    case 'A':
      if (altRefCount == 0) pressModCustom(0x04);
      if (altRefCount < 255) altRefCount++;
      return;
    case 'N':
      if (key[2] == 'L') { pressHeldKey(KEY_NUM_LOCK); }
      else if (key[2] == 'P' && key[3]) { handleNumpadKey(key); }
      return;
    case 'H': pressHeldKey(KEY_HOME); return;
    case 'I': pressHeldKey(KEY_INSERT); return;
    case 'E': pressHeldKey(KEY_END); return;
    case 'P':
      if (key[3] == 'U') pressHeldKey(KEY_PAGE_UP);
      else if (key[3] == 'D') pressHeldKey(KEY_PAGE_DOWN);
      return;
    case 'F':
      { int n = atoi(key + 2); if (n >= 1 && n <= 12) pressHeldKey(KEY_F1 + n - 1); }
      return;
  }
}

void handleKeyUp(const char* key) {
  if (strncmp(key, "*MED", 4) == 0) { TIMING_STAMP_HID('C'); consumer.release(); currentConsumerUsage = 0; return; }
  if (key[0] != '*') {
    if (key[0] && !key[1]) {
      uint8_t kc = charToHID(key[0]); if (kc != 0) releaseKeyCustom(kc);
    }
    return;
  }
  switch (key[1]) {
    case 'M':
      switch (key[2]) {
        case 'U':
          if (key[3] == 'L') mouseDirections &= ~(DIR_UP | DIR_LEFT);
          else if (key[3] == 'p') mouseDirections &= ~DIR_UP;
          else mouseDirections &= ~(DIR_UP | DIR_RIGHT);
          return;
        case 'D':
          if (key[3] == 'L') mouseDirections &= ~(DIR_DOWN | DIR_LEFT);
          else if (key[3] == 'n') mouseDirections &= ~DIR_DOWN;
          else mouseDirections &= ~(DIR_DOWN | DIR_RIGHT);
          return;
        case 'L': mouseDirections &= ~DIR_LEFT; return;
        case 'R': mouseDirections &= ~DIR_RIGHT; return;
      }
      return;
    case 'U':
      if (key[2] == 'p' && key[3]) { releaseHeldKey(KEY_UP); }
      return;
    case 'D':
      if (key[2] == 'n' && key[3]) { releaseHeldKey(KEY_DOWN); }
      else if (key[2] == 'e') { releaseHeldKey(KEY_DELETE); }
      return;
    case 'L':
      if (key[2] == 'C') { TIMING_STAMP_HID('M'); mouse.release(MOUSE_RIGHT); }
      else if (key[2] == 'f') { releaseHeldKey(KEY_LEFT); }
      return;
    case 'R':
      if (key[2] == 'C') { /* drag lock handled on key-down */ }
      else if (key[2] == 'g') { releaseHeldKey(KEY_RIGHT); }
      return;
    case 'C':
      if (key[2] == 'n') { if (!leftButtonLocked) { TIMING_STAMP_HID('M'); mouse.release(MOUSE_LEFT); } }
      else if (key[2] == 'a') { releaseHeldKey(KEY_CAPS_LOCK); }
      else if (key[2] == 't') {
        if (ctrlRefCount > 0) ctrlRefCount--;
        if (ctrlRefCount == 0) releaseModCustom(0x01);
      } else if (key[2] == 'm') {
        if (guiRefCount > 0) guiRefCount--;
        if (guiRefCount == 0) releaseModCustom(0x08);
      }
      return;
    case 'S':
      if (key[2] == 'h') {
        if (shiftRefCount > 0) shiftRefCount--;
        if (shiftRefCount == 0) releaseModCustom(0x02);
      }
      return;
    case 'A':
      if (altRefCount > 0) altRefCount--;
      if (altRefCount == 0) releaseModCustom(0x04);
      return;
    case 'N':
      if (key[2] == 'P' && key[3]) { releaseNumpadKey(key); }
      else if (key[2] == 'L') { releaseHeldKey(KEY_NUM_LOCK); }
      return;
    case 'H': releaseHeldKey(KEY_HOME); return;
    case 'I': releaseHeldKey(KEY_INSERT); return;
    case 'E': releaseHeldKey(KEY_END); return;
    case 'P':
      if (key[3] == 'U') releaseHeldKey(KEY_PAGE_UP);
      else if (key[3] == 'D') releaseHeldKey(KEY_PAGE_DOWN);
      return;
    case 'F':
      { int n = atoi(key + 2); if (n >= 1 && n <= 12) releaseHeldKey(KEY_F1 + n - 1); }
      return;
  }
}

// ====================================================================
// WebSocket
// ====================================================================
void webSocketEvent(uint8_t num, WStype_t type, uint8_t * payload, size_t length) {
  if (type == WStype_TEXT) {
    lastWSActivity = millis();
    const char* msg = (const char*)payload;

    if (strncmp(msg, "#MSPEED:", 8) == 0) {
      int v = atoi(msg + 8);
      if (v >= 1 && v <= 20) {
        mouseSpeed = v;
        Preferences p; p.begin("ikeys", false); p.putUChar("mspeed", v); p.end();
        webSocket.broadcastTXT(msg);
      }
    } else if (strncmp(msg, "#MACCEL:", 8) == 0) {
      int v = atoi(msg + 8);
      if (v >= 0 && v <= 10) {
        mouseAccel = v;
        Preferences p; p.begin("ikeys", false); p.putUChar("maccel", v); p.end();
        webSocket.broadcastTXT(msg);
      }
    } else if (strcmp(msg, "*NP") == 0) {
      if (num < MAX_WS_CLIENTS) {
        numpadMode[num] = !numpadMode[num];
        char buf[16];
        snprintf(buf, sizeof(buf), "#NP:%d", numpadMode[num] ? 1 : 0);
        webSocket.sendTXT(num, buf);
      }
    } else if (length == 1 && msg[0] == '~') {
      TIMING_STAMP_WS();
      handleKeyDown(msg);
    } else if (length > 1 && msg[0] == '~') {
      TIMING_STAMP_WS();
      handleKeyUp(msg + 1);
    } else {
      TIMING_STAMP_WS();
      handleKeyDown(msg);
    }

  } else if (type == WStype_CONNECTED) {
    Serial.printf("[WS] Client %u connected\n", num);
    wsClientCount++;
    updateDisplay();
    resetState();
    lastWSActivity = millis();
    webSocket.sendTXT(num, "Connected to iKeys HID");
    char buf[32];
    snprintf(buf, sizeof(buf), "#LED:%02X", ledState);
    webSocket.sendTXT(num, buf);
    snprintf(buf, sizeof(buf), "#MSPEED:%d", mouseSpeed);
    webSocket.sendTXT(num, buf);
    snprintf(buf, sizeof(buf), "#MACCEL:%d", mouseAccel);
    webSocket.sendTXT(num, buf);
    if (num < MAX_WS_CLIENTS) numpadMode[num] = false;
    webSocket.sendTXT(num, "#NP:0");
    snprintf(buf, sizeof(buf), "#SMT:%d", smartTypingEnabled ? 1 : 0);
    webSocket.sendTXT(num, buf);
    snprintf(buf, sizeof(buf), "#MAC:%d", macOSMode ? 1 : 0);
    webSocket.sendTXT(num, buf);
  } else if (type == WStype_DISCONNECTED) {
    Serial.printf("[WS] Client %u disconnected\n", num);
    if (wsClientCount > 0) wsClientCount--;
    updateDisplay();
    resetState();
  }
}

#include "webpage.h"

void handleRoot() {
  server.send(200, "text/html", index_html);
}

// ====================================================================
// Display helpers (AtomS3 only)
// ====================================================================
#ifdef ARDUINO_M5STACK_ATOMS3
static void bootMsg(const char* s1, const char* s2, const char* s3) {
  display.fillScreen(TFT_BLACK);
  display.setCursor(0, 0);
  display.setTextSize(2);
  display.setTextColor(TFT_CYAN, TFT_BLACK);
  display.printf("iKeys v%s", VERSION);
  display.setTextColor(TFT_WHITE, TFT_BLACK);
  int y = 18;
  if (s1) { display.setCursor(0, y); display.println(s1); y += 18; }
  if (s2) { display.setCursor(0, y); display.println(s2); y += 18; }
  if (s3) { display.setCursor(0, y); display.println(s3); }
}

static void updateDisplay() {
  display.fillScreen(TFT_BLACK);
  display.setCursor(0, 0);
  display.setTextSize(2);
  display.setTextColor(TFT_CYAN, TFT_BLACK);
  display.printf("iKeys v%s\n", VERSION);

  display.setTextColor(TFT_WHITE, TFT_BLACK);

  if (WiFi.status() == WL_CONNECTED) {
    display.println(WiFi.localIP());
    char buf[32];
    snprintf(buf, sizeof(buf), "%s.local", hostname);
    display.println(buf);
  } else {
    display.println("No WiFi");
  }
  display.printf("Clients: %d", wsClientCount);
}
#else
static void bootMsg(const char*, const char*, const char*) {}
static void updateDisplay() {}
#endif

void setup() {
  Serial.begin(115200);
  setCpuFrequencyMhz(240);
  delay(500);
  Serial.println("\n[INIT] Starting iKeys...");

#ifdef ARDUINO_M5STACK_ATOMS3
  display.begin();
#endif
  bootMsg("Starting...", nullptr, nullptr);

  USB.usbClass(0);
  USB.usbSubClass(0);
  USB.usbProtocol(0);
  if (!USB.begin()) { Serial.println("[ERR] USB init failed"); }
  keyboard.begin();
  mouse.begin();
  consumer.begin();
  keyboard.onEvent(ARDUINO_USB_HID_KEYBOARD_LED_EVENT, [](void* arg, esp_event_base_t base, int32_t id, void* data) {
    auto* ev = (arduino_usb_hid_keyboard_event_data_t*)data;
    ledState = ev->leds;
    ledStateChanged = 1;
  });
  {
    Preferences p;
    p.begin("ikeys", true);
    mouseSpeed = p.getUChar("mspeed", 5);
    mouseAccel = p.getUChar("maccel", 0);
    smartTypingEnabled = p.getUChar("smarten", 0);
    macOSMode = p.getUChar("macmode", 0);
    String h = p.getString("hostname", "ikeys");
    snprintf(hostname, sizeof(hostname), "%s", h.c_str());
    p.end();
  }

  pinMode(RESET_BUTTON_PIN, INPUT_PULLUP);

  bootMsg("WiFi connecting...", nullptr, nullptr);
  WiFiManager wm;
  wm.setHostname("ikeys");
  wm.addParameter(&customHostnameParam);
  wm.setSaveConfigCallback([]() { portalConfigSaved = true; });
  wm.setConfigPortalTimeout(180);
  wm.setConnectTimeout(20);
  if (!wm.autoConnect("iKeys-Config")) {
    Serial.println("[WARN] WiFi timeout! Proceeding anyway.");
  }
  if (WiFi.status() == WL_CONNECTED) {
    if (portalConfigSaved) {
      const char* h = customHostnameParam.getValue();
      if (h && strlen(h) > 0) {
        snprintf(hostname, sizeof(hostname), "%s", h);
        Preferences p; p.begin("ikeys", false); p.putString("hostname", hostname); p.end();
      }
    }

    char ipStr[16];
    snprintf(ipStr, sizeof(ipStr), "%d.%d.%d.%d",
             WiFi.localIP()[0], WiFi.localIP()[1],
             WiFi.localIP()[2], WiFi.localIP()[3]);

    char mdnsHostname[40];
    snprintf(mdnsHostname, sizeof(mdnsHostname), "%s.local", hostname);
    bootMsg(ipStr, mdnsHostname, nullptr);
    Serial.printf("[WiFi] Connected! IP=%s, hostname=%s\n", ipStr, hostname);
    esp_wifi_set_ps(WIFI_PS_NONE);
    Serial.println("[WiFi] Modem sleep disabled");
    ArduinoOTA.setHostname(hostname);
    // Uncomment next line and change the password to enable OTA authentication:
    // ArduinoOTA.setPassword("your-password-here");
    ArduinoOTA.onStart([]() { Serial.println("[OTA] Start"); });
    ArduinoOTA.onEnd([]() { Serial.println("[OTA] End"); });
    ArduinoOTA.onProgress([](unsigned int p, unsigned int t) {
      Serial.printf("[OTA] Progress: %u%%\r", p * 100 / t);
    });
    ArduinoOTA.onError([](ota_error_t e) {
      Serial.printf("[OTA] Error: %u\n", e);
    });

    if (MDNS.begin(hostname)) {
      Serial.printf("[mDNS] Responder started at %s\n", mdnsHostname);
      MDNS.addService("http", "tcp", 80);
      MDNS.addService("ws", "tcp", 81);
    }

    ArduinoOTA.begin();
    Serial.println("[OTA] Ready");
  } else {
    snprintf(hostname, sizeof(hostname), "ikeys");
    bootMsg("WiFi failed!", nullptr, nullptr);
  }

  bootMsg("Starting server...", nullptr, nullptr);
  server.on("/", handleRoot);
  server.on("/favicon.ico", [](){server.send(204, "text/plain", "");});
  server.on("/update", HTTP_GET, []() {
    server.sendHeader("Connection", "close");
    server.send(200, "text/html",
      "<form method='POST' action='/update' enctype='multipart/form-data'>"
      "<input type='file' name='firmware'><br><br>"
      "<input type='submit' value='Update Firmware'>"
      "</form>");
  });
  server.on("/update", HTTP_POST, []() {
    server.sendHeader("Connection", "close");
    server.send(200, "text/plain", Update.hasError() ? "FAIL" : "OK");
    if (!Update.hasError()) delay(1000);
  }, []() {
    HTTPUpload &upload = server.upload();
    static bool uploadAborted = false;
    if (upload.status == UPLOAD_FILE_START) {
      uploadAborted = false;
      Serial.printf("[OTA Web] Start: %s (%u bytes)\n", upload.filename.c_str(), upload.totalSize);
      if (!Update.begin(upload.totalSize, U_FLASH)) {
        Update.printError(Serial);
        uploadAborted = true;
      }
    } else if (upload.status == UPLOAD_FILE_WRITE) {
      if (!uploadAborted && Update.write(upload.buf, upload.currentSize) != upload.currentSize) {
        Update.printError(Serial);
      }
    } else if (upload.status == UPLOAD_FILE_ABORTED) {
      uploadAborted = false;
      Serial.println("[OTA Web] Upload aborted by client");
    } else if (upload.status == UPLOAD_FILE_END) {
      if (!uploadAborted) {
        if (Update.end(true)) {
          Serial.printf("[OTA Web] Success: %u bytes\n", upload.totalSize);
        } else {
          Update.printError(Serial);
        }
      }
    }
  });
  server.begin();
  Serial.println("[HTTP] WebServer started on port 80");

  webSocket.onEvent(webSocketEvent);
  webSocket.begin();
  Serial.println("[WS] WebSocketServer started on port 81");

  updateDisplay();
}

static void handleWdt(unsigned long now) {
  if (lastWSActivity && now - lastWSActivity > 5000 &&
      (kbdModifiers || kbdKeyCount || mouse.isPressed(MOUSE_LEFT) || mouse.isPressed(MOUSE_RIGHT) || mouseDirections || currentConsumerUsage)) {
    Serial.println("[WDT] No WS activity for 5s — resetting state");
    resetState();
    lastWSActivity = now;
  }
}

static void handleResetButton(unsigned long now) {
  bool resetPressed = digitalRead(RESET_BUTTON_PIN) == LOW;
  if (resetPressed && !resetButtonWasLow) {
    resetPressStart = now;
    resetButtonWasLow = true;
  } else if (resetPressed && resetButtonWasLow) {
    if (now - resetPressStart >= 5000) {
      Serial.println("[WiFi] Button held 5s — erasing credentials and rebooting");
#ifdef ARDUINO_M5STACK_ATOMS3
      bootMsg("Resetting", "WiFi...", nullptr);
#endif
      delay(100);
      WiFiManager wm;
      wm.resetSettings();
      delay(500);
      ESP.restart();
    }
  } else {
    resetButtonWasLow = false;
  }
}

static void handleLedSync() {
  if (ledStateChanged) {
    ledStateChanged = 0;
    char buf[16];
    snprintf(buf, sizeof(buf), "#LED:%02X", ledState);
    webSocket.broadcastTXT(buf);
  }
}

static void handleMouseMovement(unsigned long now) {
  if (mouseDirections) {
    if (!mouseMoving) { mouseMoving = true; mouseMoveStartTime = now; }
    if (now - lastMouseMove >= MOUSE_TICK_MS) {
      int8_t delta = mouseSpeed;
      if (mouseAccel > 0) {
        unsigned long held = now - mouseMoveStartTime;
        unsigned long extra = (held / 250) * mouseAccel;
        if (extra > (unsigned long)(mouseAccel * 10)) extra = mouseAccel * 10;
        if (extra > 127) extra = 127;
        delta += (int8_t)extra;
        if (delta > 127) delta = 127;
      }
      int8_t dx = 0, dy = 0;
      if (mouseDirections & DIR_LEFT)  dx -= delta;
      if (mouseDirections & DIR_RIGHT) dx += delta;
      if (mouseDirections & DIR_UP)    dy -= delta;
      if (mouseDirections & DIR_DOWN)  dy += delta;
      mouse.move(dx, dy);
      lastMouseMove = now;
    }
  } else {
    mouseMoving = false;
  }
}

static void handleDoubleClick(unsigned long now) {
  if (dclickState != DC_IDLE && now - dclickTimer >= 50) {
    dclickTimer = now;
    switch (dclickState) {
      case DC_DOWN1:
        mouse.release(MOUSE_LEFT);
        dclickState = DC_UP1;
        break;
      case DC_UP1:
        mouse.press(MOUSE_LEFT);
        dclickState = DC_DOWN2;
        break;
      case DC_DOWN2:
        mouse.release(MOUSE_LEFT);
        dclickState = DC_UP2;
        break;
      case DC_UP2:
        dclickState = DC_IDLE;
        break;
      default:
        dclickState = DC_IDLE;
    }
  }
}

void loop() {
  webSocket.loop();
  ArduinoOTA.handle();
  server.handleClient();
  unsigned long now = millis();

  TIMING_PRINT();

  handleWdt(now);
  handleResetButton(now);
  handleLedSync();
  handleMouseMovement(now);
  handleDoubleClick(now);
}
