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
#include <ESP32USBHID.h>
#ifdef ARDUINO_M5STACK_ATOMS3
#include <M5GFX.h>
#endif

#define VERSION "1.0.0"

volatile uint8_t ledState = 0;
volatile uint8_t ledStateChanged = 0;

ESP32USBHID HID;
#ifdef ARDUINO_M5STACK_ATOMS3
M5GFX display;
#endif
WebServer server(80);
WebSocketsServer webSocket(81);

// ====================================================================
// Mouse direction masks (iKeys-specific, not HID button masks)
// ====================================================================
#define MOUSE_LEFT   0x01
#define MOUSE_RIGHT  0x02
#define MOUSE_UP     0x04
#define MOUSE_DOWN   0x08

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
// HID Helpers (thin wrappers over ESP32USBHID library)
// ====================================================================
static void sendKeycode(uint8_t kc) {
  HID.pressKey(kc);
  delay(1);
  HID.releaseKey(kc);
}

// Press a key and KEEP it down until an explicit key-up arrives, so iKeys
// behaves like a real keyboard (keys can be held, e.g. for games). The library
// refcounts via keyRefCount, so the matching release is safe and idempotent.
static void pressHeldKey(uint8_t kc) {
  HID.pressKey(kc);
}

// Release a key previously held via pressHeldKey (no-op if not pressed).
static void releaseHeldKey(uint8_t kc) {
  HID.releaseKey(kc);
}

static void mouseDoubleClick() {
  if (dclickState == DC_IDLE) {
    dclickState = DC_DOWN1;
    HID.setMouseButtons(HID.getMouseButtons() | MOUSE_BTN_LEFT);
    dclickTimer = millis();
  }
}

static void toggleLeftLock() {
  leftButtonLocked = !leftButtonLocked;
  if (leftButtonLocked) {
    HID.setMouseButtons(HID.getMouseButtons() | MOUSE_BTN_LEFT);
  } else {
    HID.setMouseButtons(HID.getMouseButtons() & ~MOUSE_BTN_LEFT);
  }
  if (wsClientCount > 0) {
    webSocket.broadcastTXT(leftButtonLocked ? "#DRAG:1" : "#DRAG:0");
  }
}

static void resetState() {
  HID.releaseAll();
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
  uint8_t kc = ESP32USBHID::charToHID(c);
  if (kc == 0) return;
  uint8_t savedMod = HID.getModifierState();
  bool doCaps = smartTypingShiftNext && ((c >= 'a' && c <= 'z') || (c >= 'A' && c <= 'Z'));
  if (ESP32USBHID::needsShift(c) || doCaps) HID.setModifierState(savedMod | MOD_LSHIFT);
  if (doCaps) smartTypingShiftNext = false;
  HID.pressKey(kc);
  HID.setModifierState(savedMod);

  if (smartTypingEnabled) {
    if (c == 'q' || c == 'Q') {
      sendKeycode(ESP32USBHID::charToHID('u'));
    } else if (c == '.' || c == '!' || c == '?') {
      sendKeycode(KEY_SPACE);
      sendKeycode(KEY_SPACE);
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
  if (usage) HID.pressConsumer(usage);
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
          if (key[3] == 'L') { mouseDirections |= MOUSE_UP | MOUSE_LEFT; }
          else if (key[3] == 'p') { mouseDirections |= MOUSE_UP; }
          else { mouseDirections |= MOUSE_UP | MOUSE_RIGHT; }
          return;
        case 'D':
          if (key[3] == 'L') { mouseDirections |= MOUSE_DOWN | MOUSE_LEFT; }
          else if (key[3] == 'n') { mouseDirections |= MOUSE_DOWN; }
          else { mouseDirections |= MOUSE_DOWN | MOUSE_RIGHT; }
          return;
        case 'L': mouseDirections |= MOUSE_LEFT; return;
        case 'R': mouseDirections |= MOUSE_RIGHT; return;
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
      if (key[2] == 'C') { HID.setMouseButtons(HID.getMouseButtons() | MOUSE_BTN_RIGHT); }
      else if (key[2] == 'f') { pressHeldKey(KEY_LEFT); }
      return;
    case 'R':
      if (key[2] == 'C') { toggleLeftLock(); }
      else if (key[2] == 'g') { pressHeldKey(KEY_RIGHT); }
      return;
    case 'S':
      if (key[2] == 'h') {
        if (shiftRefCount == 0) HID.pressModifier(MOD_LSHIFT);
        if (shiftRefCount < 255) shiftRefCount++;
      } else if (key[2] == 'm') { smartTypingEnabled = !smartTypingEnabled; { Preferences p; p.begin("ikeys", false); p.putUChar("smarten", smartTypingEnabled); p.end(); } webSocket.broadcastTXT(smartTypingEnabled ? "#SMT:1" : "#SMT:0"); }
      else if (key[2] == 'H') pressHeldKey(KEY_TAB);
      else mouseDoubleClick();
      return;
    case 'C':
      if (key[2] == 'n') { HID.setMouseButtons(HID.getMouseButtons() | MOUSE_BTN_LEFT); }
      else if (key[2] == 'a') pressHeldKey(KEY_CAPS_LOCK);
      else if (key[2] == 't') {
        if (ctrlRefCount == 0) HID.pressModifier(MOD_LCTRL);
        if (ctrlRefCount < 255) ctrlRefCount++;
      } else {
        if (guiRefCount == 0) HID.pressModifier(MOD_LGUI);
        if (guiRefCount < 255) guiRefCount++;
      }
      return;
    case 'A':
      if (altRefCount == 0) HID.pressModifier(MOD_LALT);
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
  if (strncmp(key, "*MED", 4) == 0) { HID.releaseConsumer(); return; }
  if (key[0] != '*') {
    if (key[0] && !key[1]) {
      uint8_t kc = ESP32USBHID::charToHID(key[0]); if (kc != 0) HID.releaseKey(kc);
    }
    return;
  }
  switch (key[1]) {
    case 'M':
      switch (key[2]) {
        case 'U':
          if (key[3] == 'L') mouseDirections &= ~(MOUSE_UP | MOUSE_LEFT);
          else if (key[3] == 'p') mouseDirections &= ~MOUSE_UP;
          else mouseDirections &= ~(MOUSE_UP | MOUSE_RIGHT);
          return;
        case 'D':
          if (key[3] == 'L') mouseDirections &= ~(MOUSE_DOWN | MOUSE_LEFT);
          else if (key[3] == 'n') mouseDirections &= ~MOUSE_DOWN;
          else mouseDirections &= ~(MOUSE_DOWN | MOUSE_RIGHT);
          return;
        case 'L': mouseDirections &= ~MOUSE_LEFT; return;
        case 'R': mouseDirections &= ~MOUSE_RIGHT; return;
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
      if (key[2] == 'C') { HID.setMouseButtons(HID.getMouseButtons() & ~MOUSE_BTN_RIGHT); }
      else if (key[2] == 'f') { releaseHeldKey(KEY_LEFT); }
      return;
    case 'R':
      if (key[2] == 'C') { /* drag lock handled on key-down */ }
      else if (key[2] == 'g') { releaseHeldKey(KEY_RIGHT); }
      return;
    case 'C':
      if (key[2] == 'n') { if (!leftButtonLocked) HID.setMouseButtons(HID.getMouseButtons() & ~MOUSE_BTN_LEFT); }
      else if (key[2] == 'a') { releaseHeldKey(KEY_CAPS_LOCK); }
      else if (key[2] == 't') {
        if (ctrlRefCount > 0) ctrlRefCount--;
        if (ctrlRefCount == 0) HID.releaseModifier(MOD_LCTRL);
      } else if (key[2] == 'm') {
        if (guiRefCount > 0) guiRefCount--;
        if (guiRefCount == 0) HID.releaseModifier(MOD_LGUI);
      }
      return;
    case 'S':
      if (key[2] == 'h') {
        if (shiftRefCount > 0) shiftRefCount--;
        if (shiftRefCount == 0) HID.releaseModifier(MOD_LSHIFT);
      }
      return;
    case 'A':
      if (altRefCount > 0) altRefCount--;
      if (altRefCount == 0) HID.releaseModifier(MOD_LALT);
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
      handleKeyDown(msg);
    } else if (length > 1 && msg[0] == '~') {
      handleKeyUp(msg + 1);
    } else {
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
  delay(500);
  Serial.println("\n[INIT] Starting iKeys...");

#ifdef ARDUINO_M5STACK_ATOMS3
  display.begin();
#endif
  bootMsg("Starting...", nullptr, nullptr);

  HID.begin();
  HID.onLED([](uint8_t s){ ledState = s; ledStateChanged = 1; });
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
      (HID.getModifierState() || HID.getPressedCount() || HID.getMouseButtons() || mouseDirections || HID.getConsumerState())) {
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
      if (mouseDirections & MOUSE_LEFT)  dx -= delta;
      if (mouseDirections & MOUSE_RIGHT) dx += delta;
      if (mouseDirections & MOUSE_UP)    dy -= delta;
      if (mouseDirections & MOUSE_DOWN)  dy += delta;
      HID.moveMouse(dx, dy);
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
        HID.setMouseButtons(HID.getMouseButtons() & ~MOUSE_BTN_LEFT);
        dclickState = DC_UP1;
        break;
      case DC_UP1:
        HID.setMouseButtons(HID.getMouseButtons() | MOUSE_BTN_LEFT);
        dclickState = DC_DOWN2;
        break;
      case DC_DOWN2:
        HID.setMouseButtons(HID.getMouseButtons() & ~MOUSE_BTN_LEFT);
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
  ArduinoOTA.handle();
  server.handleClient();
  webSocket.loop();
  unsigned long now = millis();
  handleWdt(now);
  handleResetButton(now);
  handleLedSync();
  handleMouseMovement(now);
  handleDoubleClick(now);
}
