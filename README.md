# Real-Time Neurofeedback EEG System on ESP32

A real-time EEG/neurofeedback prototype built on a Wemos Mini ESP32, MicroPython, Bluetooth UART, and an embedded web dashboard.

The system receives ThinkGear-compatible EEG packets from a BrainMind Wave Mobile 2 through an HC-05 Bluetooth serial module, parses the incoming stream on the ESP32, exposes live data as JSON, and serves a mobile-friendly dashboard over the local WiFi network.

> This project is an embedded systems and neurofeedback engineering prototype. It is not a certified medical device and should not be used for clinical diagnosis without validation, calibration, and regulatory review.

---

## Technical Description

This project demonstrates a complete low-power EEG data path using only an ESP32 and MicroPython. The ESP32 acts as both the acquisition controller and the local web server:

- Connects to a WiFi network in station mode.
- Receives EEG packets over UART from an HC-05 Bluetooth module.
- Parses ThinkGear/NeuroSky-style packets.
- Validates frame checksum.
- Extracts raw EEG samples from `0x80` packets.
- Extracts EEG power bands from `0x83` packets when available.
- Maintains a circular signal buffer.
- Publishes live data through a `/data` JSON endpoint.
- Serves an HTML/JavaScript dashboard directly from the ESP32.

The main goal is to provide a portable, browser-based neurofeedback interface that can run on local hardware without a cloud backend, desktop software, or external server.

---

## System Architecture

The data path is intentionally simple and local-first:

```text
┌──────────────────────────┐
│ BrainMind Wave Mobile 2  │
│ EEG headset              │
└────────────┬─────────────┘
             │ Bluetooth serial stream
             ▼
┌──────────────────────────┐
│ HC-05 Bluetooth module   │
│ Serial bridge            │
└────────────┬─────────────┘
             │ UART @ 57600 baud
             │ TX -> ESP32 GPIO16 (RX)
             │ RX -> ESP32 GPIO17 (TX)
             ▼
┌──────────────────────────┐
│ Wemos Mini ESP32         │
│ MicroPython runtime      │
└────────────┬─────────────┘
             │
             ▼
┌──────────────────────────┐
│ ThinkGear Parser         │
│ Header, payload, checksum│
│ 0x80 raw, 0x83 power     │
└────────────┬─────────────┘
             │
             ▼
┌──────────────────────────┐
│ EEG Processing Layer     │
│ Circular buffer          │
│ Visual scaling           │
│ Runtime counters         │
└────────────┬─────────────┘
             │
             ▼
┌──────────────────────────┐
│ Embedded HTTP Server     │
│ /      -> dashboard      │
│ /data  -> JSON stream    │
└────────────┬─────────────┘
             │ WiFi LAN
             ▼
┌──────────────────────────┐
│ Smartphone Browser       │
│ Mobile dashboard         │
└──────────────────────────┘
```

---

## Hardware

| Component | Function |
| --- | --- |
| Wemos Mini ESP32 | Main embedded controller, UART receiver, ThinkGear parser, WiFi web server |
| HC-05 Bluetooth module | Bluetooth-to-UART serial bridge between the headset stream and the ESP32 |
| BrainMind Wave Mobile 2 | EEG headset producing ThinkGear-compatible serial packets |
| Smartphone client | Browser-based dashboard client connected to the same local WiFi network |
| Local WiFi network | LAN transport between the ESP32 web server and the mobile dashboard |

### UART Wiring

| HC-05 Pin | ESP32 Pin | Purpose |
| --- | --- | --- |
| TX | GPIO16 (RX) | EEG serial data into ESP32 |
| RX | GPIO17 (TX) | Optional serial transmit path from ESP32 |
| GND | GND | Shared reference |
| VCC | Compatible supply | HC-05 power input |

Default serial configuration:

```text
UART:     UART1
RX:       GPIO16
TX:       GPIO17
Baudrate: 57600
Protocol: ThinkGear / NeuroSky-style packets
```

---

## Project Structure

```text
neurofeedback/
├── main.py
├── config.py
├── wifi.py
├── eeg_parser.py
├── web_server.py
├── dashboard.py
└── README.md
```

### `main.py`

Application entry point. It wires together the full runtime:

- Loads configuration constants.
- Connects to WiFi.
- Initializes ESP32 UART.
- Creates the `EEGParser`.
- Creates the embedded `WebServer`.
- Starts the main acquisition/server loop.

### `eeg_parser.py`

ThinkGear packet parser and EEG data model.

Responsibilities:

- Maintains an internal receive buffer for partial UART reads.
- Resynchronizes on the ThinkGear header `0xAA 0xAA`.
- Validates payload length and checksum.
- Parses raw wave packets (`0x80`) as signed 16-bit samples.
- Parses ASIC EEG power packets (`0x83`) when present.
- Maintains circular buffers for:
  - `raw.Fp1`: visually scaled signal for the dashboard.
  - `raw.Fp1Raw`: original signed raw values.
- Tracks runtime counters such as `RawSamples`, `ValidFrames`, `BadChecksum`, and `EEGPowerFrames`.
- Provides `get_json_data()` for the `/data` endpoint.

The current implementation includes a temporary visual scaling path so the dashboard can show motion even when only raw `0x80` packets are present.

### `web_server.py`

Minimal embedded HTTP server for MicroPython.

Responsibilities:

- Opens a TCP socket on the configured server port.
- Uses socket timeouts so UART processing can continue.
- Calls `parser.procesar()` in the main loop.
- Serves:
  - `/` as the HTML dashboard.
  - `/data` as JSON.
- Runs garbage collection during the loop to reduce memory pressure.

### `dashboard.py`

Self-contained HTML, CSS, and JavaScript dashboard.

Responsibilities:

- Displays a patient/test control header.
- Draws EEG power bars.
- Renders a live frontal EEG trace on a canvas.
- Polls `/data` periodically using `fetch()`.
- Updates the matrix table and waveform display in the browser.

### `wifi.py`

WiFi station-mode helper.

Responsibilities:

- Activates the ESP32 WiFi interface.
- Connects to the configured SSID.
- Waits until connected.
- Prints the local dashboard URL.

### `config.py`

Central configuration module.

Responsibilities:

- WiFi credentials import.
- UART ID, baudrate, RX/TX pins, and timeout.
- HTTP server port and timeout.
- EEG buffer size and maximum ThinkGear payload length.

Recommended credential pattern:

```python
try:
    from secrets import SSID, PASSWORD
except ImportError:
    SSID = "TU_WIFI"
    PASSWORD = "TU_PASSWORD"
```

Keep real credentials out of public repositories.

---

## EEG Protocol

The project targets ThinkGear/NeuroSky-style serial packets.

### Frame Format

```text
0xAA 0xAA [payload_length] [payload bytes...] [checksum]
```

### Header

Each frame starts with two sync bytes:

```text
AA AA
```

The parser uses this marker to resynchronize when bytes are dropped, corrupted, or received mid-frame.

### Payload Length

The byte after the header defines the payload size. The parser rejects payloads larger than the configured `MAX_PAYLOAD_LENGTH`.

### Checksum

Checksum is calculated as:

```text
checksum = 255 - (sum(payload) & 0xFF)
```

If the received checksum does not match the calculated checksum, the frame is discarded and `BadChecksum` is incremented.

### `0x80` Raw Wave

Raw EEG packets use an extended ThinkGear code:

```text
0x80 0x02 [high_byte] [low_byte]
```

The two bytes are decoded as a signed 16-bit integer:

```python
value = (high_byte << 8) | low_byte
if value & 0x8000:
    value -= 0x10000
```

The raw value is published as `raw.Fp1Raw`. A centered and scaled version is published as `raw.Fp1` for dashboard visualization.

### `0x83` EEG Power

EEG power packets use:

```text
0x83 0x18 [24 bytes]
```

The 24-byte block contains eight unsigned 24-bit values:

1. Delta
2. Theta
3. Low Alpha
4. High Alpha
5. Low Beta
6. High Beta
7. Low Gamma
8. High Gamma

The parser exposes derived aggregate values:

- `Alpha = LowAlpha + HighAlpha`
- `Beta = LowBeta + HighBeta`
- `Gamma = LowGamma + HighGamma`

When `0x83` packets are not present, the dashboard can still display raw activity derived from `0x80` packets for visual feedback.

---

## Current Features

- Real-time EEG packet acquisition over UART.
- ThinkGear frame synchronization.
- Payload length validation.
- Checksum validation.
- Raw wave decoding from `0x80` packets.
- EEG power decoding from `0x83` packets when available.
- Circular signal buffer.
- JSON endpoint at `/data`.
- Embedded dashboard served by the ESP32.
- Mobile browser access over local WiFi.
- Visual signal scaling for live feedback.
- Runtime parser metrics:
  - `RawSamples`
  - `RawValue`
  - `ValidFrames`
  - `BadChecksum`
  - `EEGPowerFrames`

---

## Installation

### 1. Install Thonny

Download and install Thonny:

```text
https://thonny.org/
```

Use Thonny as the MicroPython IDE and file transfer tool.

### 2. Flash MicroPython on the ESP32

In Thonny:

1. Connect the Wemos Mini ESP32 over USB.
2. Open `Tools -> Options -> Interpreter`.
3. Select a MicroPython ESP32 interpreter.
4. Install or update MicroPython firmware if required.
5. Confirm the REPL is available.

### 3. Wire the HC-05 to the ESP32

Use the configured UART pins:

```text
HC-05 TX -> ESP32 GPIO16 (RX)
HC-05 RX -> ESP32 GPIO17 (TX)
GND      -> GND
```

Confirm the HC-05 serial baudrate is set to `57600`.

### 4. Configure WiFi

Recommended: create a `secrets.py` file on the ESP32:

```python
SSID = "your_wifi_name"
PASSWORD = "your_wifi_password"
```

Keep `secrets.py` private and do not commit it to GitHub.

### 5. Upload Project Files

Using Thonny, upload these files to the MicroPython device:

```text
main.py
config.py
wifi.py
eeg_parser.py
web_server.py
dashboard.py
secrets.py
```

Make sure files are saved to the device, not only opened from the PC.

### 6. Run the System

In Thonny, run:

```python
exec(open("main.py").read())
```

Or open `main.py` and press Run.

The console should print a URL similar to:

```text
Sistema QEEG Online listo en: http://10.254.0.45
Servidor web iniciado en puerto 80
```

---

## Usage

1. Power the EEG headset and HC-05 module.
2. Confirm the Bluetooth serial link is active.
3. Run `main.py` on the ESP32.
4. Open the printed ESP32 IP address from a phone on the same WiFi network.
5. Press `Iniciar Test`.
6. Watch:
   - EEG power bars.
   - Signal matrix values.
   - Live frontal trace.

### JSON Endpoint

Open:

```text
http://<esp32-ip>/data
```

Example fields:

```json
{
  "raw": {
    "Fp1": [0, 12, -18],
    "Fp1Raw": [120, 384, -512]
  },
  "fp1": {
    "RawSamples": 100,
    "RawValue": -512,
    "ValidFrames": 100,
    "BadChecksum": 0,
    "EEGPowerFrames": 0
  }
}
```

### Interpreting the Current Signal

- `raw.Fp1Raw` is the raw signed value decoded from `0x80`.
- `raw.Fp1` is a visually scaled version used by the dashboard.
- `EEGPowerFrames > 0` means `0x83` power-band packets are being received.
- `EEGPowerFrames = 0` with increasing `RawSamples` means the headset is currently sending raw wave packets, but not EEG power packets.
- High `BadChecksum` values indicate serial corruption, baudrate mismatch, unstable Bluetooth serial data, or packet parsing issues.

---

## Troubleshooting

### `AttributeError: 'EEGParser' object has no attribute 'uart'`

Cause: the constructor in `eeg_parser.py` is not named correctly on the ESP32.

Correct:

```python
def __init__(self, uart, buffer_size=35, max_payload_length=169):
```

Incorrect:

```python
def init(...)
def _init_(...)
```

Verify directly on the device:

```python
for i, line in enumerate(open("eeg_parser.py")):
    if "init" in line:
        print(i + 1, repr(line))
```

### Dashboard Opens But Signal Is Flat

Check `/data`:

- If `RawSamples` increases, UART and parser are working.
- If `raw.Fp1` stays near zero, adjust visual scaling in `eeg_parser.py`.
- If `RawSamples` does not increase, verify Bluetooth/UART input.

### No Data Arrives From UART

Verify:

- HC-05 TX is connected to ESP32 GPIO16.
- HC-05 RX is connected to ESP32 GPIO17.
- GND is shared.
- HC-05 baudrate is `57600`.
- The headset is paired/connected and transmitting serial data.

### WiFi Does Not Connect

Check:

- `SSID` and `PASSWORD`.
- ESP32 is within range.
- Phone and ESP32 are on the same local network.
- `secrets.py` exists on the device if using private credentials.

### Browser Cannot Open Dashboard

Check:

- ESP32 printed an IP address.
- Phone is connected to the same WiFi network.
- Use `http://<esp32-ip>`, not `https://`.
- Port is configured as `80`.

### High `BadChecksum`

Possible causes:

- Serial noise.
- Incorrect baudrate.
- Bluetooth link instability.
- Partial packet handling issue.
- Power instability on HC-05 or ESP32.

---

## Future Improvements

Planned engineering directions:

- Digital filters for raw EEG:
  - DC removal
  - notch filter
  - band-pass filter
- Real FFT-based spectral analysis on-device or in-browser.
- Clinically meaningful band-power calculations.
- Better smoothing and scaling for dashboard traces.
- CSV export of raw and processed sessions.
- Historical session storage.
- Multi-channel abstractions.
- Neurofeedback training modes.
- Adaptive thresholds.
- Event markers for blinking, jaw movement, and attention tasks.
- Machine learning experiments for signal classification.
- WebSocket or Server-Sent Events streaming instead of polling.
- WiFi reconnection and startup timeout handling.
- More robust socket lifecycle management.

---

## Credits

Author:

```text
Kevin Surribas
```

Technical mentorship:

```text
Gonzalo Surribas
```

---

## License

MIT License.

This repository is intended for educational, research, and portfolio use. Any medical or clinical application requires proper validation, safety testing, and regulatory compliance.
