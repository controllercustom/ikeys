# iKeys — Wireless Assistive Keyboard

iKeys turns an ESP32-S3 into a wireless USB HID keyboard. A tablet or phone displays large, customizable key layouts in a browser, and taps are forwarded over WiFi to the ESP32, which types them on any computer via USB — no software installation required on the target machine.

```
[ Tablet ] --WiFi--> [ ESP32-S3 ] --USB--> [ Computer ]
                      (keys pressed        (sees standard
                       via WebSocket)       USB keyboard)
```

This is a modern, cost-effective replacement for assistive keyboards like IntelliKeys.

## Features

- **Zero software on the target PC** — shows up as a standard USB keyboard
- **Web-based UI** — any tablet/phone with a browser becomes the input surface
- **8×12 CSS Grid layout** with customizable keys, modifiers, and a mouse navigation zone
- **Numpad overlay** — tap "Num Pad" to switch to a dual keypad overlay with proper USB HID keypad codes
- **Mouse emulation** — directional pad, left/right click, double-click, drag lock
- **Mouse controls** — adjust speed (1–20) and acceleration (0–10) via in-grid buttons on the numpad overlay
    - **Smart Typing** — auto-inserts spaces after punctuation (`,` `;` `:` `.` `!` `?`) and auto-capitalizes the next letter after `.` `!` `?`; persists across reboots and page refreshes
    - **macOS Mode** — persistent toggle (occupies the main-grid top-row cell where Num Lock used to be) that accommodates macOS HID behavior: greys out keys with no macOS function (Insert) and relabels the numpad Num Lock keys to "Clear"; persisted to flash
    - **Slide-typing** — drag your finger between keys to type multiple characters in one motion
- **WiFiManager** — no hardcoded credentials; configure WiFi via captive portal on first boot
- **Customizable mDNS hostname** — default `ikeys.local`; change via the "Device hostname" field in the WiFiManager captive portal; persists across reboots
- **WiFi credential reset** — hold the BOOT button (GPIO0) or AtomS3 button (GPIO41) for 5 seconds to erase WiFi credentials and reboot into captive portal
- **OTA updates** — upload new firmware wirelessly via `espota.py` or browser
- **Debug bar** — shows real-time WebSocket status, last key pressed, and Num Lock / Caps Lock / Scroll Lock LED state
- **Multi-client support** — concurrent key presses from multiple tablets are reference-counted; each press is tracked independently so the host never sees phantom releases
- **AtomS3 display** — shows IP address, hostname, and firmware version on the 128×128 screen (M5Stack AtomS3 only)

## Hardware Requirements

| Component | Required | Notes |
|---|---|---|
| ESP32-S3 dev board with native USB | Yes | e.g. ESP32-S3-DevKitC-1, M5Stack AtomS3 |
| USB-C cable | Yes | Connects ESP32 to target computer |
| Tablet / Phone | Yes | Any device with a web browser |
| USB-A to USB-C adapter | Maybe | If the target computer only has USB-A ports |

The ESP32-S3's **native USB port** (USB-OTG) is required for HID — the UART/serial-only port won't work. Ensure your board breaks out the native USB pins (D+, D-).

### Supported Boards

**Generic ESP32-S3 Dev Module** — works with any standard ESP32-S3 development board.

**M5Stack AtomS3** — compact form factor with a built-in 128×128 IPS display that shows the device IP and hostname at boot.

## Getting Started

### 1. Flash the Firmware

### Building with Arduino IDE (Recommended)

1. **Install ESP32 board support**: Open *File → Preferences*, add `https://espressif.github.io/arduino-esp32/package_esp32_index.json` to *Additional Boards Manager URLs*, then go to *Tools → Board → Boards Manager*, search for **ESP32** and install.

2. **Install libraries**: Go to *Tools → Manage Libraries* and install:
    - **WiFiManager** by tzapu
    - **M5GFX** by M5Stack (required for AtomS3 only)
    - **WebSockets** by Markus Sattler
    - **Built-in ESP32 USB HID libraries** (`USBHIDKeyboard`, `USBHIDRelativeMouse`, `USBHIDConsumerControl`) — these ship with the ESP32 Arduino core, no extra install needed.

3. **Select your board**:
   - **Generic ESP32-S3**: *Tools → Board → ESP32 Arduino → ESP32S3 Dev Module*
   - **AtomS3**: *Tools → Board → ESP32 Arduino → M5AtomS3*

4. **Configure USB mode** (both boards): *Tools → USB Mode → **USB-OTG (TinyUSB)***

5. **Set CDC On Boot**:
   - Both boards: *Tools → USB CDC On Boot → **Disabled***

6. **Set partition scheme (AtomS3 only)**: *Tools → Partition Scheme → **8M with spiffs (3MB APP/1.5MB SPIFFS)***

7. **Open the sketch**: *File → Open* and select `ikeys.ino` from the project folder.

8. **Connect and upload**: Plug the ESP32-S3 into your computer via USB. Select the correct port under *Tools → Port*, then click the **Upload** button (→).
   - **AtomS3 bootloader mode**: Since CDC ACM is disabled, the AtomS3 requires manual bootloader entry. Press and hold the small Reset button on the side for 2–3 seconds, then release. The LED turns green and solid to confirm download mode. Upload immediately after.

### Building with Arduino CLI

Install [Arduino CLI](https://arduino.github.io/arduino-cli/), the ESP32 core, and required libraries:

```bash
arduino-cli core install esp32:esp32@3.3.10
arduino-cli lib install "WiFiManager@2.0.17" "M5GFX@0.2.26" "WebSockets@2.7.2"
# No external HID library needed — built-in USBHIDKeyboard/Mouse/ConsumerControl used
```

| Component | Version |
|---|---|
| ESP32 Arduino Core | 3.3.10 |
| WiFiManager | 2.0.17 |
| M5GFX | 0.2.26 |
| WebSockets | 2.7.2 |

Compile and upload via serial:

```bash
# Compile — uses sketch.yaml profiles for reproducible builds
arduino-cli compile --profile esp32s3 .
arduino-cli compile --profile atoms3 .

# Serial upload (no profile available for upload — use full FQBN):
# Generic ESP32-S3 dev module
arduino-cli upload -p /dev/ttyUSB0 --fqbn "esp32:esp32:esp32s3:USBMode=default,CDCOnBoot=default" .

# M5Stack AtomS3
# With CDC ACM disabled, the AtomS3 must be in bootloader (download) mode before upload.
# Press and hold the small Reset button on the side for 2–3 seconds, then release.
# The internal LED turns green and solid to confirm bootloader mode.
arduino-cli upload -p /dev/ttyACM0 --fqbn "esp32:esp32:m5stack_atoms3:PartitionScheme=default_8MB,USBMode=default,CDCOnBoot=default" .
```

Run `arduino-cli` as a normal user (not `sudo`) — it needs no elevated privileges for compile or upload (serial access works because your user is in the `dialout` group). Running it as root creates a root-owned `~/.cache/arduino`, which then blocks later non-root compiles; if that happens, remove it with `sudo rm -rf ~/.cache/arduino`.

### 1b. Enable Latency Measurement (Optional)

Uncomment `#define TIMING` near the top of `ikeys.ino` (line ~42) and reflash. The firmware will then print microsecond-granularity `[TIMING] K/M/C ws=... hid=... fw_us=...` lines over Serial for every key press, mouse click, or media key action. Use `test/measure_latency.py` to collect statistics:

```bash
# Keyboard
sudo python3 test/measure_latency.py --host <ip> --type key --key a --samples 50

# Mouse left click
sudo python3 test/measure_latency.py --host <ip> --type mouse --samples 30

# Media play/pause
sudo python3 test/measure_latency.py --host <ip> --type media --samples 30
```

Measured firmware processing is **12–16 µs** and end-to-end is **2.9–6.2 ms** across all HID types. Re-comment `// #define TIMING` and reflash for normal operation (saves ~588 bytes flash).

### 2. Connect to WiFi

On first boot, the ESP32 starts a WiFi access point named **iKeys-Config**. Connect to it with your phone or tablet — a captive portal should appear automatically. Select your home WiFi network and enter the password. The device will reboot and connect.

### 3. Find the Device on Your Network

Once connected, the device advertises itself via mDNS as `ikeys.local` (default; you can set a custom hostname in the WiFiManager captive portal; the hostname is saved to flash and persists across reboots). You can also check your router's DHCP client list or use a network scanner.

Open a browser and navigate to:

```
http://ikeys.local
```

If you set a custom hostname, use that instead of `ikeys`.

### 4. Plug into the Target Computer

Connect the ESP32-S3 to the computer that should receive the keystrokes via its **native USB port** (not the UART/serial port). The computer will recognize it as a standard USB keyboard — no drivers needed.

### 5. Use the Keyboard

The web UI shows an 8-row × 12-column keyboard grid with:

- **QWERTY layout** with shift-key symbols
- **Function keys** (F1–F12)
- **Navigation keys** (arrows, home, end, pgup, pgdn)
- **Mouse zone** (navy blue keys on the right) — directional pad, left/right click, double-click, drag lock
- **Modifier keys** (Shift, Ctrl, Alt, Cmd) with visual active-state feedback
- **Caps Lock, Mac Mode, Insert, Delete, Tab, Enter, Space, Backspace** (Num Lock appears on the numpad overlay)

Tap a key on your tablet — the keystroke appears on the target computer instantly via WebSocket. Drag across keys to slide-type multiple characters in one motion.

#### Numpad Overlay

Tap **Num Pad** (top row, right side of the grid) to switch to a dedicated numpad overlay based on the same 8×12 grid as the main keyboard. Dual number keypads appear in the lower corners:

- **Left keypad** (cols 1–4, rows 4–8) — standard 5-row numpad layout
- **Right keypad** (cols 9–12, rows 4–8) — mirrored for left-handed use

Each keypad: `NL` `/` `*` `−` / `7` `8` `9` `+` / `4` `5` `6` / `1` `2` `3` `Enter` / `0` `Del`

Keys send proper USB HID keypad codes — fully compatible with spreadsheet and data-entry applications. Use whichever side is most comfortable.

#### Mouse Config (In-Grid Controls)

Mouse Speed and Acceleration are adjusted directly from the numpad overlay via in-grid buttons in the top-middle area (rows 1–2, cols 3–11):

`Spd−` `Speed: 5` `Spd+` / `Acl−` `Accel: 0` `Acl+` / `✕ Exit`

Tap **Spd−** or **Spd+** to decrease/increase speed (1–20). Tap **Acl−** or **Acl+** to decrease/increase acceleration (0–10). Current values are shown on the display keys between the buttons. Settings persist across reboots.

Tap **✕ Exit** (or the Num Pad key on the main grid) to return to the main keyboard.

#### Media Keys

Media keys appear in the center of the numpad overlay (rows 3–5, columns 5–8):

| Key | Action |
|---|---|
| Vol− / Vol+ | Volume down / up |
| Mute | Toggle audio mute |
| Play | Play / Pause toggle |
| Prev / Next | Previous / next track |
| RW / FF | Rewind / fast forward |

**Mute**, **Vol−**, **Vol+**, and **Play** work reliably with most media players. **Prev**, **RW**, **FF**, and **Next** use less common HID usages and are not well supported by many media players; they may need additional configuration or driver support on the host.

#### Smart Typing

Tap the **Smart Typing** key to enable Smart Typing mode (key glows amber). While active:

- **Auto-space**: a single space is inserted after `,` and `;`; two spaces after `:` (client-side)
- **Dual-space + capitalize**: two spaces and the next letter is capitalized after `.`, `!`, and `?` (server-side)
- **Quick fix**: tapping `Q` while holding a direction sends `u` — a shortcut for the common "quack" typo

Tap **Smart Typing** again to disable. The setting is stored in flash and persists across reboots and page refreshes.

#### Debug Bar

A slim bar at the top shows:
- **WS**: WebSocket connection status (connected / disconnected)
- **Key**: the last key you pressed
- **NL / CL / SL**: Num Lock, Caps Lock, and Scroll Lock LED state synced from the host computer (updates in real time when you toggle those locks)

#### Multiple Tablets

Multiple tablets or phones can connect to the same iKeys device simultaneously. Each client independently chooses between the main grid and numpad overlay — one tablet can show the numpad while another shows the main keyboard. All taps from all clients are forwarded to the USB host as a single combined keyboard. This is useful when a helper uses one tablet to assist the user who has their own tablet. Simply open the same URL (`http://ikeys.local` or your custom hostname) on each device.

Each key press is reference-counted on the server. If two clients press the same key (e.g., both hold `Shift`), the modifier stays active until *both* clients release it. This prevents phantom releases and ensures reliable multi-user operation.

### OTA Updates

Once the device is online, you can upload new firmware wirelessly over the network with `arduino-cli` (no serial connection needed):

```bash
# Compile + OTA in one step (uses sketch.yaml profiles)
# Generic dev module
arduino-cli compile --profile esp32s3 . --output-dir tmp/ikeys-build \
  && arduino-cli upload -p ikeys.local --upload-field password="" \
     --fqbn "esp32:esp32:esp32s3:USBMode=default,CDCOnBoot=default" .

# M5Stack AtomS3
arduino-cli compile --profile atoms3 . --output-dir tmp/ikeys-build \
  && arduino-cli upload -p ikeys.local --upload-field password="" \
     --fqbn "esp32:esp32:m5stack_atoms3:PartitionScheme=default_8MB,USBMode=default,CDCOnBoot=default" .
```

Replace `ikeys.local` with your custom hostname if you set one. If OTA password protection is enabled (see below), change `password=""` to `password="<pw>"`.

Alternatively, use the **web OTA page** at `http://ikeys.local/update` to upload a `.bin` from your browser, or the legacy `espota.py` tool shipped with the ESP32 core (replace `<arduino_path>` with your Arduino CLI install location):

```bash
python3 <arduino_path>/packages/esp32/hardware/esp32/<version>/tools/espota.py \
  -i ikeys.local -f tmp/ikeys-build/ikeys.ino.bin -r -d
```

#### OTA Password (Optional)

By default, OTA updates require no password — anyone on your network can upload firmware. To enable password protection:

1. Open `ikeys.ino` and find the line:
   ```cpp
   // ArduinoOTA.setPassword("your-password-here");
   ```
2. Remove the `//` comment and change `your-password-here` to a strong password of your choice.
3. Recompile and upload the firmware via serial or OTA.

Once enabled, add `-a "<password>"` to all `espota.py` commands:

```bash
python3 <arduino_path>/packages/esp32/hardware/esp32/<version>/tools/espota.py \
  -a "your-password-here" -i ikeys.local -f tmp/ikeys-build/ikeys.ino.bin -r -d
```

## Running Tests

The project includes a Python test suite for offline validation of HID keycode tables, WebSocket protocol messages, smart typing rules, and data structure integrity:

```bash
pip3 install -r test/requirements.txt
python3 -m pytest test/ -v
```

No hardware needed — all 238 offline tests run using transcribed PROGMEM tables and JS data arrays (the `test/e2e/` hardware tests additionally require a connected board).

### End-to-End Hardware Tests

`test/e2e/` drives the **real board** over its WebSocket control port (81) and observes the USB HID output it produces via `python3-evdev` on the host. These are skipped unless you explicitly run them, so the default `pytest test/` run stays offline.

Requirements:

- `python3-evdev` (system package, e.g. `apt install python3-evdev` on Raspberry Pi OS) — for reading the board's HID events.
- `websocket-client` (`pip3 install -r test/requirements.txt`).
- **Root** — the harness grabs the evdev device so the board's keystrokes don't leak into your console. Run with `sudo`.
- The board's USB HID must be connected to the host, and its WebSocket must be reachable (it must be on a network the host can route to).

Run them:

```bash
# Board already up — tell the harness its address (IP or hostname):
sudo IKEYS_HOST=192.168.1.x python3 -m pytest test/e2e -v

# Or flash the sketch over /dev/ttyUSB0, then auto-discover the IP from the
# board's UART boot log, then run the tests:
sudo python3 -m pytest test/e2e -v --ikey-flash

# Equivalent one-liners:
pytest test/e2e -v -m e2e          # select by marker
```

The harness sends each key (e.g. `a`, `*PgUp`, `*NP7`, `*Shft`) over WebSocket and asserts the exact evdev `EV_KEY` press+release the board emits — including a dedicated regression that `PgUp`/`PgDn`/`Insert` each produce their own distinct code. Mouse tests assert `BTN_LEFT`/drag-lock and `REL_X` motion.

If the board can't be reached, the tests skip with a message telling you to set `IKEYS_HOST` (or `--ikey-host`) or use `--ikey-flash`. `--ikey-port` / `--ikey-fqbn` override the serial port and board FQBN.

## Resetting WiFi Credentials

To connect the device to a different WiFi network, hold the button for 5 seconds:

- **Generic ESP32-S3 Dev Module**: hold the **BOOT** button (GPIO0)
- **M5Stack AtomS3**: hold the built-in button (GPIO41) — the display shows "Resetting WiFi..."

The saved credentials are erased and the device reboots into the **iKeys-Config** captive portal. Connect to it from your phone or tablet and configure the new network.

## Key Layout

The keyboard is an 8×12 CSS Grid with three zones:

| Rows | Columns 1–9 | Columns 10–12 |
|---|---|---|
| 1–2 | System + Function keys (Esc, F1–F12, Num Lock, etc.) | — |
| 3–4 | Numbers / Symbols + QWERTY letters | Backspace |
| 5 | Home row (A–L) | **← ↑ ↗** (mouse nav) |
| 6 | Bottom alpha (Z–M) + punctuation | **← ※ →** (mouse click + nav) |
| 7 | Modifiers + Space + remaining punctuation | **↙ ↓ ↘** (mouse nav) |
| 8 | Ctrl, Alt, Cmd, arrow keys, Enter | **※※** (dbl-click), **⬗ R** (right-click), **⬖ Drag** (drag lock) |

Additional keys on the grid include **Smart Typing** (toggle), **Mac Mode** (toggle), **Num Pad** (numpad toggle), and LED status indicators in the debug bar. (The numpad overlay also has Num Lock keys, labelled "NL", which become "Clear" when macOS Mode is on.)

## License

MIT
