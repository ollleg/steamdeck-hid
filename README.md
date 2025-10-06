# steamdeck-hid

A reusable Python library for handling Steam Deck controller inputs using `evdev` and `hid`. This library allows you to monitor button presses, analog stick movements, touch pads, and other inputs from the Steam Deck in a non-blocking, asynchronous manner. It supports event subscription via callbacks, making it suitable for integration into games, automation scripts, or custom applications on SteamOS or other Linux environments.

The library is designed for Linux systems (tested on Steam Deck with SteamOS) and requires root privileges or appropriate permissions to access input devices (e.g., via `sudo` or adding your user to the `input` group).

## Features
- Asynchronous event reading from multiple input devices.
- Support for buttons (A/B/X/Y, D-Pad, triggers, bumpers, etc.), analog sticks, touch pads, and power/volume buttons.
- Customizable device paths for flexibility across different setups.
- Event subscription model: Register callbacks to react to input changes.
- Helper functions to list available devices and decode HID reports.
- Lightweight with minimal dependencies.

## Installation

Install the library via pip:

```bash
pip install steamdeck-hid
```

### Dependencies
- `evdev`: For reading input events from `/dev/input/event*` devices.
- `hid`: For raw HID report reading from `/dev/hidraw*`.

These are automatically installed as dependencies. Note: This library is Linux-specific due to its reliance on `evdev` and HID raw devices.

If you encounter permission issues (e.g., "Permission denied" when accessing devices), run your script with `sudo` or add your user to the `input` group:

```bash
sudo usermod -aG input $USER
```

Log out and back in for changes to take effect.

## Quick Start

Here's a basic example to get started. This script lists devices, initializes the input handler, subscribes to events, and prints changes:

```python
import asyncio
from steamdeck_hid import SteamDeckInput, list_all_devices

async def main():
    # Optional: List all available input devices to verify paths
    list_all_devices()

    # Initialize with default paths (customize if needed)
    sdi = SteamDeckInput(
        device_paths=['/dev/input/event5', '/dev/input/event2', '/dev/input/event8', '/dev/input/event14'],
        hidraw_path='/dev/hidraw2'
    )

    # Define a callback for input changes
    def my_callback(key, value):
        print(f"Input event: '{key}' changed to {value}")

    # Subscribe the callback
    sdi.add_listener(my_callback)

    # Start listening (runs indefinitely until interrupted)
    print("Listening for Steam Deck inputs... Press Ctrl+C to stop.")
    await sdi.start()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Program terminated by user")
    except Exception as e:
        print(f"Error: {e}")
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

### Multiple Callbacks
You can add multiple listeners:

```python
def callback1(key, value):
    if key == 'POWER':
        print("Power button pressed!")

def callback2(key, value):
    print(f"Generic event: {key} = {value}")

sdi.add_listener(callback1)
sdi.add_listener(callback2)
```

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
The library automatically grabs and ungrabs devices. On exit (e.g., Ctrl+C), it releases resources. Handle exceptions in your `main` function for robustness.

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
- **High CPU usage**: The polling rate is 1ms; adjust `asyncio.sleep(0.001)` in the source if needed.

For issues, open a ticket on the [GitHub repository](https://github.com/yourusername/steamdeck-hid) (replace with your actual repo URL).