# AGENTS.md - iKeys Assistive Keyboard

## Overview
Assistive keyboard project (v0.4) using an ESP32-S3 that acts as a USB HID device (Keyboard/Mouse). It hosts a Web UI to trigger keystrokes on the connected computer.

## Key Technical Details
- **Hardware**: ESP32-S3 with native USB HID support. Two board targets:
  - Generic ESP32-S3 Dev Module (`esp32:esp32:esp32s3`)
  - M5Stack AtomS3 (`esp32:esp32:m5stack_atoms3`) with 128x128 display (GC9107, SPI)
- **Connectivity**: WiFi via WiFiManager — first boot starts `iKeys-Config` AP for credential setup.
- **Communication**:
  - Client $\rightarrow$ ESP32: WebSocket on port 81 (keypresses, config updates). HTTP on port 80 serves the HTML page only.
  - ESP32 $\rightarrow$ Host PC: USB HID (Keyboard + Mouse) via custom class wrapping `USBHID` (extracted into standalone `ESP32USBHID` library at https://github.com/controllercustom/ESP32USBHID).
- **mDNS**: Default `ikeys.local`; configurable via the "Device hostname" field in the WiFiManager captive portal, persisted to Preferences across reboots.
- **OTA**: ArduinoOTA enabled — upload wirelessly via `arduino-cli upload --upload-field password=""`. Optional password authentication (commented out in source — see README to enable).
- **Web OTA**: Upload firmware via browser at `http://<hostname>.local/update`.
- **Diagnostics**: Serial monitor at `115200` baud.
- **Display (AtomS3 only)**: Shows IP, hostname, version on boot; static after init. Uses M5GFX library.
- **Mouse**: Tick-based movement (20ms interval). Speed (1–20) and acceleration (0–10) adjustable at runtime via in-grid buttons on the numpad overlay, persisted to Preferences (`mspeed`, `maccel`). Acceleration adds `held/250 * accel` to base delta, capped at `accel * 10`.
- **Key dispatch**: `handleKeyDown`/`handleKeyUp` use `switch(key[1])` for O(1) dispatch by key group instead of linear `strcmp` scan. Media keys (`*MED*`) are dispatched via an early-return `strncmp` check *before* the switch to avoid falling into the mouse (`case 'M'`) handler. Numpad keycodes ordered by frequency in lookup table.
- **Mouse double-click**: Non-blocking state machine (`DC_IDLE→DC_DOWN1→DC_UP1→DC_DOWN2→DC_UP2`) in `loop()` — no `delay()` calls.
- **Smart Typing persists**: Saved to Preferences (`smarten`), survives reboot and page refresh. Not cleared by `resetState()`.
- **macOS mode**: Persistent toggle (Preferences `macmode`, key `*Mac`, status `#MAC:0/1`) accommodating macOS HID quirks. Toggle occupies the main-screen top-row cell where **Num Lock** used to be (Num Lock is a no-op on macOS, so it was repurposed). Not cleared by `resetState()`; broadcast on toggle and sent on WS connect. When ON, the client greys out (`.mac-disabled`) keys with no macOS function (**Insert**), and relabels the numpad **NL** keys to **Clear** (HID usage `0x53` = "Keypad NumLock and Clear" is exactly what a Mac numpad Clear key sends, so it is a label-only change). Keys that still work on macOS (Home/End/PgUp/PgDn, media, etc.) are left active.
- **macOS vs Windows HID differences**: (1) Mouse required a 5-byte report — see Historical Bugs. (2) macOS has no Num Lock; usage `0x53` acts as Clear, and the keypad is always numeric (PC "Num-Lock-off" nav does not exist). (3) macOS ignores Caps Lock presses shorter than ~100ms (accidental-keystroke prevention) — resolved because Caps Lock is now held until finger-up like every other key, so a real finger hold always exceeds 100ms. (4) Insert/PrintScreen/ScrollLock have no macOS function. (5) Modifiers are intentionally left as-is (GUI=⌘, Alt=⌥); the dedicated ⌘ key is used for Mac shortcuts.
- **Held keys (real-keyboard behavior)**: All non-modifier keys are pressed on key-down and released only on the matching key-up — they stay reported as DOWN while the finger is held (so games/key-combos like WASD/arrows/F-keys work). Implemented via `pressHeldKey()`/`releaseHeldKey()` (`sendKeycode`'s auto-release is used only for the smart-typing auto-injected `u`/space taps). The HID boot keyboard report allows up to 6 simultaneous keys. Disconnect calls `resetState()` (global release).
- **Embedded webpage**: CSS active-state rules consolidated via grouped selectors; JS modifier keys dispatched via lookup object; `pointerup`/`pointercancel` share one handler.

## Build & Upload
```bash
# First install the ESP32USBHID library from GitHub into your Arduino libraries folder:
#   curl -L -o tmp/ESP32USBHID.zip https://github.com/controllercustom/ESP32USBHID/archive/refs/heads/main.zip
#   unzip -o tmp/ESP32USBHID.zip -d tmp/
#   cp -r tmp/ESP32USBHID-main ~/Arduino/libraries/ESP32USBHID
# Or just clone directly: git clone https://github.com/controllercustom/ESP32USBHID ~/Arduino/libraries/ESP32USBHID

# Compile (USBMode=default enables USB-OTG/TinyUSB for HID)
arduino-cli compile --fqbn "esp32:esp32:esp32s3:USBMode=default,CDCOnBoot=default" .

# Compile for AtomS3 (USBMode=default, CDCOnBoot=default, PartitionScheme=default_8MB enables 3MB OTA slots)
arduino-cli compile --fqbn "esp32:esp32:m5stack_atoms3:PartitionScheme=default_8MB,USBMode=default,CDCOnBoot=default" .

# Serial upload (AtomS3: must be in bootloader/download mode first — press and hold
# the small Reset button on the side for 2–3 seconds, release; LED turns green solid)
arduino-cli upload -p /dev/ttyACM0 --fqbn "esp32:esp32:m5stack_atoms3:PartitionScheme=default_8MB,USBMode=default,CDCOnBoot=default" .

# OTA upload (device must be online, no password = empty string for --upload-field).
# If OTA password is enabled, change password="" to password="<pw>".
arduino-cli upload -p <hostname>.local --upload-field password="" --fqbn "esp32:esp32:m5stack_atoms3:PartitionScheme=default_8MB,USBMode=default,CDCOnBoot=default" .

# Or compile + OTA in one step (AtomS3):
arduino-cli compile --fqbn "esp32:esp32:m5stack_atoms3:PartitionScheme=default_8MB,USBMode=default,CDCOnBoot=default" . --output-dir tmp/ikeys-build \
  && arduino-cli upload -p <hostname>.local --upload-field password="" --fqbn "esp32:esp32:m5stack_atoms3:PartitionScheme=default_8MB,USBMode=default,CDCOnBoot=default" .

# Or compile + OTA in one step (generic dev module):
arduino-cli compile --fqbn "esp32:esp32:esp32s3:USBMode=default,CDCOnBoot=default" . --output-dir tmp/ikeys-build \
  && arduino-cli upload -p <hostname>.local --upload-field password="" --fqbn "esp32:esp32:esp32s3:USBMode=default,CDCOnBoot=default" .
```

## Testing

```bash
# Install dependencies
pip3 install -r test/requirements.txt

# Run all tests
python3 -m pytest test/ -v

# Run a specific test file
python3 -m pytest test/test_hid_keycodes.py -v

# Run a specific test class
python3 -m pytest test/test_smart_typing.py::TestServerSideAutoSpace -v
```

### End-to-end hardware tests (`test/e2e/`)
These drive the **real board** over its WebSocket control port (81) and observe the USB HID output via `python3-evdev`. They are skipped unless explicitly selected, so the default `pytest test/` run stays 100% offline.

```bash
# Board already up — give its address (IP/hostname):
sudo IKEYS_HOST=192.168.1.x python3 -m pytest test/e2e -v

# Or flash over /dev/ttyUSB0 and auto-discover the IP from the UART boot log:
sudo python3 -m pytest test/e2e -v --ikey-flash
```

Requirements: `python3-evdev` (system package), `websocket-client` (in `test/requirements.txt`), **root** (the harness grabs the evdev device so keystrokes don't leak to the console), and a board whose WebSocket is reachable from the host. If unreachable, tests skip with guidance to set `IKEYS_HOST`/`--ikey-host` or use `--ikey-flash`. Files: `hid_mapping.py` (HID usage → evdev code), `firmware.py` (build+upload+serial IP discovery), `evdev_util.py` (`EventWatcher`), and `test_basic.py`/`test_keys.py`/`test_mouse.py`. Device detection auto-matches both boards' HID names (`Espressif Systems ESP32S3_DEV …` for the dev module, `Espressif Systems M5STACK_ATOMS3 …` for the AtomS3). When running under `sudo`, the test deps must be importable as root — if `websocket-client` was installed to the user site, export `PYTHONPATH="$(python3 -c 'import site;print(site.getusersitepackages())')"` (and `PATH=/home/pi/bin:$PATH` if arduino-cli lives in the user `bin`).

The test suite covers:
- **HID keycode tables** — `charToHID` mapping for all 128 ASCII values, `needsShift` lookup table, keycode constants
- **WebSocket protocol** — message formats for key down/up, config commands (`#MSPEED:`/`#MACCEL:`), server status (`#LED:`/`#SMT:`/`#NP:`/`#DRAG:`/`#MAC:`)
- **Smart typing** — client-side auto-space rules (`,`/`;` → 1 space, `:` → 2), server-side dual-space + capitalize after `.` `!` `?`, Q→u quack shortcut
- **Grid data structure** — all 91 cells have required fields, shift-symbol pairs, nav-key classes, span bounds, no duplicate codes
- **Numpad data structure** — entry validity, left/right keypad symmetry, `*NP` key prefixes, config controls
- **Mouse config** — speed (1–20) and accel (0–10) range clamping, config message format, accel calculation
- **LED state** — bitmask parsing (bits 0=NL, 1=CL, 2=SL), all 8 combinations, round-trip `#LED:XX` format

All tests run offline (no hardware needed). Fixtures in `conftest.py` transcribe the PROGMEM tables and JS data arrays directly from the source.

## Web UI
- Embedded as a C++ raw string literal (`R"rawliteral(...)rawliteral"`) in `webpage.h` (included via `#include "webpage.h"` from the `.ino` file).
- The keyboard layout is defined in a `gridData` JavaScript array inside the raw literal.
- The keyboard spec is in `@keyboard_description.md` — an 8-row x 12-column CSS Grid with a navy "Blue Zone" navigation block on the right (rows 5-8, cols 10-12).
- Extra keys without an `l` (label) property display their `k` value directly; the `k` string is sent via WebSocket when clicked.
- **Numpad overlay** (`#numpad`): An 8-row × 12-column CSS Grid (same dimensions as main keyboard). Contains dual number keypads in the lower-left and lower-right corners (cols 1–4 and 9–12, rows 4–8), each sending `*NP*`-prefixed HID key codes (0x54–0x63). Mouse Speed/Accel controls in the top-middle area (rows 1–2, cols 3–11) using in-grid buttons (`*SpdD`/`*SpdU`/`*AclD`/`*AclU`) — no separate config overlay. Exit button (✕, row 2, cols 5–8) toggles back to main keyboard.
- **Reconcile display** (`reconcileDisplay()`): Manages visibility between grid and numpad layers (no separate config panel). Called by `toggleNumpad()`.
- **Mouse config keys**: Four in-grid buttons (Spd−, Spd+, Acl−, Acl+) adjust values client-side, update display keys (`*SpdVal`, `*AclVal`), and send `#MSPEED:`/`#MACCEL:` to server for persistence. Values sync bidirectionally.
- **Smart Typing auto-space**: Client-side `sendDown()` inserts one ` ` (press+release) after `,` or `;`, two spaces after `:`. Server-side inserts two spaces after `.` `!` `?` and sets `smartTypingShiftNext` to capitalize the next letter. State is persisted to Preferences and restored on boot.
- **LED status sync**: `querySelectorAll` used for `*NL` and `*CaLk` keys so both grid and numpad buttons reflect Caps Lock / Num Lock LED state simultaneously.
- **macOS mode toggle**: Main-screen top-row cell is a persistent **Mac Mode** toggle (`*Mac`), not Num Lock (Num Lock is a no-op on macOS). On `#MAC:1` the client adds `.mac-active` to `*Mac` and `.mac-disabled` to `*Ins` (Insert has no macOS function); the two numpad `*NL` keys relabel to **Clear** (HID usage `0x53` = "Keypad NumLock and Clear" — exactly the Mac numpad Clear code, so it is label-only); and the numpad dual-key nav secondary labels (Home/End/PgUp/PgDn/arrows/Ins/Del) dim via `#numpad .key-dual .mac-dim .key-bot` (digits in `.key-top` stay full opacity — they still type). Toggling sends `#MAC:0/1`; persisted to Preferences `macmode`; sent on WS connect; not cleared by `resetState()`.

## Historical Bugs (preserve fixes)
- **Missing `=>`**: `ws.onclose`/`ws.onerror` arrow functions were missing `=>`, causing a JS SyntaxError that prevented the entire script from running.
- **`innerHTML` operator precedence**: `cell.l || cell.k === ' ' ? 'SPACE' : cell.k` grouped as `(cell.l || (cell.k === ' ')) ? 'SPACE' : cell.k`, making every key with an `l` property show "SPACE". Fix: `cell.l || (cell.k === ' ' ? 'SPACE' : cell.k)`.
- **CSS clipping**: Default `<button>` padding + missing `box-sizing: border-box` on `.key` caused keys to overflow their grid cells, clipped by `body { overflow: hidden }`. Fix: flexbox body layout, `box-sizing: border-box; padding: 0` on `.key`.
- **Stuck modifier highlight**: Single `pressedBtn` variable could only track one finger. Tapping another key while holding a modifier overwrote the reference, so the modifier's `pointerup` found `pressedBtn === null` and never removed `.mod-active`. Fix: `Map<pointerId, {btn,k}>` with `setPointerCapture`, plus `pointercancel` handler.
- **Slide typing broken**: `setPointerCapture` locked `pointermove` target to original element. Sliding to another key did not trigger a new press/release. Fix: `document.addEventListener('pointermove', ...)` with `document.elementFromPoint()` to detect actual key under finger each frame.
- **Slide stops after 3-4 keys**: CSS grid `gap: 4px` had no `touch-action` property, defaulting to `auto`. Crossing a gap could trigger `pointercancel` or throttle `pointermove`. Also, sliding off-key deleted the `pressedBtns` entry, preventing subsequent re-entry onto keys. Fix: `body { touch-action: none }`, and keep entry alive when pointer is not over any key.
- **Missing `USB.begin()`**: With `CDCOnBoot=default`, `Serial` maps to UART0, not USBCDC. `USBHID::begin()` creates semaphores but does NOT call `USB.begin()`. The USJ peripheral stayed active and TinyUSB never initialized. Fix: call `USB.begin()` explicitly after `USB.usbClass(0)` etc. and before `HID.begin()`.
- **Tab key sent wrong HID code**: Position 9 in `charToHID` PROGMEM table was `0x09` (keyboard 9) instead of `0x2B` (keyboard Tab). Fix: changed entry from `0x09` to `0x2B`.
- **Auto-space press without release**: Initial auto-space for `,` `;` `:` sent only `ws.send(' ')` (press) without `ws.send('~ ')` (release), leaving the Space key stuck down. Fix: send paired press+release sequences.
- **LED sync missed duplicated keys**: `<button>` elements for `*NL` and `*CaLk` exist on both the grid and numpad, but handler used `getElementById`/`querySelector` (single element). Fix: changed to `querySelectorAll` + `forEach` to toggle `.mod-active` on all instances.
- **Smart Typing lost on page refresh**: `resetState()` cleared `smartTypingEnabled` on disconnect, so server sent `#SMT:0` to the new client even when persisted value was true. Fix: removed `smartTypingEnabled = false` from `resetState()` — only transient `smartTypingShiftNext` is cleared.
- **Mouse double-click blocked loop**: `mouseDoubleClick()` used three `delay(50)` calls, blocking the event loop for 150ms. Fix: state machine in `loop()` (`DC_IDLE→DC_DOWN1→DC_UP1→DC_DOWN2→DC_UP2`) with 50ms timer per phase.
- **`needsShift()` O(n) strchr**: Called `strchr()` on every single-character keystroke. Fix: PROGMEM bool lookup table for O(1) per call.
- **String heap allocations in hot path**: `handleKeyDown`/`handleKeyUp` used `const String&` with `key.substring().toInt()` for F-keys. Fix: `const char*` + `atoi()` — no heap alloc per keystroke.
- **Mouse accel overflow**: `int extra = (held / 250) * mouseAccel` could overflow with large `held`. Fix: `unsigned long extra`, capped at 127 before signed cast.
- **Hostname not persisted**: `WiFiManagerParameter` values are in-memory only — custom hostname reverted to `"ikeys"` on reboot. Fix: save hostname to Preferences via `setSaveConfigCallback` + `Preferences.putString`; restore on boot from `Preferences.getString`.
- **Media keys falling into mouse handler**: Media keys prefixed `*MED` share `key[1]` = `'M'` with mouse movement codes. Without an early `strncmp` check in both `handleKeyDown` and `handleKeyUp`, the press was silently ignored and the release fell through to `case 'M'` / `key[2] = 'E'` (no match), leaving the consumer key stuck in the pressed state. Fix: early-return `strncmp(key, "*MED", 4)` check at the top of both handlers, *before* the `switch(key[1])` block.
- **Mouse report dropped by macOS**: `TUD_HID_REPORT_DESC_MOUSE` declares a **5-byte** report (buttons, X, Y, wheel, AC-Pan), but the library sent only **4 bytes** (`moveMouse` built a 4-byte buffer and `sendMouse` called `SendReport(2, data, 4)`). macOS strictly validates report length against the descriptor and silently drops the undersized report (Windows tolerates it — which is why the mouse worked on Windows but not macOS). Fix is in the **`ESP32USBHID` library** (`~/Arduino/libraries/ESP32USBHID/src/ESP32USBHID.cpp`): `moveMouse` and `setMouseButtons` now build a 5-byte `{btns, dx, dy, wheel, pan}` report and `sendMouse`/`SendReport` use length 5 (`uint8_t report[5]`, `SendReport(2, data, 5)`); released via `uint8_t mzero[5]`. A new `scrollMouse(wheel, pan)` helper was added for wheel/pan. Must also be pushed upstream to https://github.com/controllercustom/ESP32USBHID.

- **Caps Lock hold method**: Chosen as **hold-until-release** (same as every other key) — no special FSM. A real finger hold always exceeds macOS's ~100ms Caps Lock debounce, so it toggles correctly on macOS without a timed workaround.
- **Held-key design decision**: Previously most non-character keys went through `sendKeycode()` which auto-released after 1ms, so they could not be held (broke game key-combos). They now use `pressHeldKey()`/`releaseHeldKey()` so the key stays DOWN until the matching key-up, matching real-keyboard behavior. `sendKeycode` is retained only for the smart-typing auto-injected `u`/space taps.
- **Nav-key dispatch misassignment**: `case 'I'` (the `*Ins` key) was wired to `KEY_PAGE_UP`, and `case 'P'` only checked `key[3] == 'p'` (which matches no key) so both `*PgUp` and `*PgDn` fell through to `KEY_INSERT` — making PgUp and PgDn behave identically as Insert. Fix: `case 'I'` → `KEY_INSERT`; `case 'P'` → `if (key[3] == 'U') KEY_PAGE_UP; else if (key[3] == 'D') KEY_PAGE_DOWN;`. Mirrored identically in `handleKeyUp`. Regression test: `test/test_dispatch_nav.py` parses the actual C++ control flow to assert the correct HID code per nav key.
- **ESP32USBHID library HID constants rotated (the real root cause of the PgUp/PgDn/Insert bug)**: In `~/Arduino/libraries/ESP32USBHID/src/ESP32USBHID.h` the keyboard/keypad constants `KEY_PAGE_UP`, `KEY_PAGE_DOWN`, `KEY_INSERT` were assigned the wrong codes — they were **rotated by one** vs the USB HID Usage Tables (Keyboard/Keypad page 0x07): `KEY_PAGE_UP` was `0x49` (actually Insert), `KEY_PAGE_DOWN` was `0x4B` (actually Page Up), `KEY_INSERT` was `0x4E` (actually Page Down). Correct spec values: Insert = `0x49`, Page Up = `0x4B`, Page Down = `0x4E`. Fix: `KEY_PAGE_UP` = `0x4B`, `KEY_PAGE_DOWN` = `0x4E`, `KEY_INSERT` = `0x49`. All other `KEY_*` constants in the header were already correct. **Must be pushed upstream** to https://github.com/controllercustom/ESP32USBHID. The regression test `test/test_dispatch_nav.py` now also asserts the resolved hex code equals the spec value, so a future constant rotation is caught.

## Development Notes
- WiFi credentials are configured via WiFiManager's captive portal (`iKeys-Config` AP) on first boot.
- **Library**: `ESP32USBHID` at `~/Arduino/libraries/ESP32USBHID/` (install from https://github.com/controllercustom/ESP32USBHID) wraps the USB HID layer. Provides `ESP32USBHID` class with `pressKey`/`releaseKey`, `pressModifier`/`releaseModifier`, `moveMouse`, `setMouseButtons`, `scrollMouse`, `pressConsumer`/`releaseConsumer`, `releaseAll`, `onLED` callback, and static `charToHID`/`needsShift` lookup tables. All constants (`MOD_*`, `KEY_*`, `MOUSE_BTN_*`, `MEDIA_*`) defined in the header.
- **USB configuration**: The library's `begin()` calls `USB.usbClass(0)`, `USB.usbSubClass(0)`, `USB.usbProtocol(0)`, then `USB.begin()`, then `hid.begin()`. CDC ACM disabled via `CDCOnBoot=default` board option — OTG port exposes three HID interfaces: Keyboard (report ID 1), Mouse (report ID 2), Consumer Control (report ID 3). No USB serial debug output; use UART0 (pins 43/44).
- The sketch creates a global `ESP32USBHID HID;` and calls `HID.begin()` in `setup()`. All HID state (modifierState, pressedKeys, keyRefCount, mouseBtns, consumerUsage) is managed inside the library. The sketch retains iKeys-specific state: modifier refcounts for multi-client, mouse direction bitmask, double-click FSM, smart typing, web server/WS.
- **AtomS3 serial upload**: With CDC ACM disabled, the AtomS3's USB port offers no serial interface for auto-reset. Press and hold the small Reset button on the side for 2–3 seconds, release — LED turns green solid confirming download mode. Then run `arduino-cli upload`.
- **Run arduino-cli as a normal user (never `sudo`)**: The `pi` user is already in the `dialout` group, so serial uploads to `/dev/ttyUSB0`/`/dev/ttyACM0` and all OTA (network) uploads work without root. Running arduino-cli as root creates a **root-owned `~/.cache/arduino`**; subsequent non-root compiles then fail with permission errors. If that happens, clear it with `sudo rm -rf ~/.cache/arduino` — `arduino-cli cache clean` only empties the cache but leaves the root-owned directory in place, so it does NOT fix the ownership problem.
- **Flash usage**: AtomS3 ~38% (1,280,559 bytes) with `default_8MB` partition scheme, generic ESP32-S3 ~89% (1,169,573 bytes).
