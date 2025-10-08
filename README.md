# steamdeck-hid

A reusable Python library for handling Steam Deck controller inputs using `evdev` and `hid`. This library allows you to monitor button presses, analog stick movements, touch pads, and other inputs from the Steam Deck using background threads for non-blocking operation in the main loop. It uses a polling model, making it suitable for integration into games, automation scripts, or custom applications on SteamOS or other Linux environments.

The library is designed for Linux systems (tested on Steam Deck with SteamOS) and requires root privileges or appropriate permissions to access input devices (e.g., via `sudo` or adding your user to the `input` group).

## Features
- Background thread-based event reading from multiple input devices for non-blocking main loop.
- Support for buttons (A/B/X/Y, D-Pad, triggers, bumpers, etc.), analog sticks, touch pads, and power/volume buttons.
- Customizable device paths for flexibility across different setups.
- Adjustable polling interval to control responsiveness and CPU usage.
- Polling model: Retrieve events with `get_events()` similar to `pygame.event.get()`.
- Helper functions to list available devices and decode HID reports.
- Lightweight with minimal dependencies.

## Installation

Install the library via pip (works on Linux, macOS, and other platforms, but full functionality is Linux-only):

```bash
pip install steamdeck-hid
```

- On Linux/Steam Deck: Automatically includes all dependencies for full support.
- On non-Linux systems (e.g., macOS, Windows): Installation succeeds, but usage of core features (e.g., `SteamDeckInput`) will raise an error indicating lack of support.

### Dependencies
- `hid`: For raw HID report reading (cross-platform, always installed).
- `evdev`: For reading input events from `/dev/input/event*` devices (automatically installed on Linux only).

Note: This library is Linux-specific due to its reliance on `evdev` and HID raw devices. On non-Linux systems, you can still use standalone functions like `decode_steamdeck_report` (if they don't require `evdev`), but device reading features are unavailable.

If you encounter permission issues on Linux (e.g., "Permission denied" when accessing devices), run your script with `sudo` or add your user to the `input` group:

```bash
sudo usermod -aG input $USER
```

Log out and back in for changes to take effect.

## Quick Start

Here's a basic example to get started. This script lists devices, initializes the input handler, and polls for events in a loop:

```python
import time
from steamdeck_hid import SteamDeckInput, list_all_devices

# Optional: List all available input devices to verify paths
list_all_devices()

sdi = SteamDeckInput(
    device_paths=['/dev/input/event5', '/dev/input/event2', '/dev/input/event8', '/dev/input/event14'],
    hidraw_path='/dev/hidraw2',
    polling_interval=0.001  # Default: 1ms; adjust for CPU/responsiveness trade-off
)

print("Listening for Steam Deck inputs... Press Ctrl+C to stop.")

try:
    while True:
        events = sdi.get_events()
        for key, value in events:
            print(f"Input event: '{key}' changed to {value}")
        time.sleep(0.01)  # Small sleep to avoid high CPU in the main loop
except KeyboardInterrupt:
    print("Program terminated by user")
finally:
    sdi.stop()
```

Run this script with:

```bash
python your_script.py
```

Or with sudo if needed:

```bash
sudo python your_script.py
```

### Expected Output
When you press buttons or move sticks/pads, you'll see output like:
```
Input event: 'A' changed to True
Input event: 'LEFT_STICK_X' changed to 1234
Input event: 'VOLUME_UP' changed to True
```

## Advanced Usage

### Customizing Device Paths
If your Steam Deck's device paths differ (e.g., due to kernel updates or hardware variations), use `list_all_devices()` to identify them and pass custom paths:

```python
sdi = SteamDeckInput(
    device_paths=['/dev/input/eventX', '/dev/input/eventY'],  # Replace with your paths
    hidraw_path='/dev/hidrawZ'
)
```

The power/volume buttons are typically on one specific device (default: `/dev/input/event5`). The library handles this internally.

### Adjusting Polling Interval
To balance responsiveness and CPU usage, set the `polling_interval` (in seconds) during initialization. Lower values (e.g., 0.001 for 1ms) provide faster updates but may increase CPU load; higher values (e.g., 0.01 for 10ms) reduce CPU usage at the cost of slight delay.

```python
sdi = SteamDeckInput(polling_interval=0.01)  # 10ms interval
```

Default is 0.001 (1ms).

### Supported Inputs
The library tracks the following keys in the state dictionary (booleans for buttons, integers for axes):

- Buttons: `A`, `B`, `X`, `Y`, `UP`, `DOWN`, `LEFT`, `RIGHT`, `L1`, `R1`, `L2`, `R2`, `L4`, `L5`, `R4`, `R5`, `STEAM`, `MENU`, `WINDOW`, `MORE`, `POWER`, `VOLUME_UP`, `VOLUME_DOWN`
- Presses/Touches: `LEFT_PAD_PRESS`, `RIGHT_PAD_PRESS`, `LEFT_PAD_TOUCH`, `RIGHT_PAD_TOUCH`, `LEFT_STICK_PRESS`, `RIGHT_STICK_PRESS`, `LEFT_STICK_TOUCH`, `RIGHT_STICK_TOUCH`
- Axes: `LEFT_STICK_X`, `LEFT_STICK_Y`, `RIGHT_STICK_X`, `RIGHT_STICK_Y`, `LEFT_PAD_X`, `LEFT_PAD_Y`, `RIGHT_PAD_X`, `RIGHT_PAD_Y`

Changes are only triggered for significant movements (e.g., >200 for sticks, >100 for pads) to reduce noise.

### Decoding HID Reports Manually
If you need low-level access, use the standalone `decode_steamdeck_report` function:

```python
from steamdeck_hid import decode_steamdeck_report

buttons_state = {}
data = b'your_raw_hid_data_here'  # Example: read from hid device
decode_steamdeck_report(data, buttons_state)
print(buttons_state)  # {'A': True, 'LEFT_STICK_X': 0, ...}
```

### Error Handling and Cleanup
The library automatically grabs and ungrabs devices. Always call `stop()` in a `finally` block to stop threads and release resources properly, especially on exit (e.g., Ctrl+C).

## Contributing
Contributions are welcome! Fork the repository on GitHub, make changes, and submit a pull request. Please include tests and update documentation.

## License
MIT License

Copyright (c) 2025 Oleh Polishchuk

See the [LICENSE](LICENSE) file for details.

## Troubleshooting
- **Device not found**: Use `list_all_devices()` to confirm paths. Update paths accordingly.
- **Permission denied**: Run with `sudo` or adjust group permissions.
- **No events**: Ensure the Steam Deck is connected and not in desktop mode with inputs routed elsewhere.
- **High CPU usage**: Increase the `polling_interval` (e.g., to 0.01 for 10ms) to reduce polling frequency.
- **Program doesn't exit on Ctrl+C**: Ensure `stop()` is called in a `finally` block after catching `KeyboardInterrupt`.

For issues, open a ticket on the [GitHub repository](https://github.com/ollleg/steamdeck-hid).