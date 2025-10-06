# MIT License
# Copyright (c) 2025 Oleh Polishchuk

import asyncio
from evdev import InputDevice, categorize, ecodes, list_devices
import os
import struct
import hid

def list_all_devices():
    """List all available input devices with capabilities."""
    print("Available input devices:")
    devices = [InputDevice(path) for path in list_devices()]
    for device in devices:
        print(f"InputDevice('{device.path}'), Name: {device.name}, Phys: {device.phys}")
        capabilities = device.capabilities(verbose=True)
        if 'EV_KEY' in capabilities:
            print(f"  Supported keys: {capabilities[('EV_KEY', ecodes.EV_KEY)]}")
    return devices

def decode_steamdeck_report(data, buttons_state: dict):
    """Decode a Steam Deck HID report for buttons and axes."""
    if len(data) < 12:  # Adjust based on actual report size
        return

    # Example mapping (based on Steam Controller/Steam Deck community reverse-engineering)
    button_byte = data[8]
    buttons_state["R2"] = (button_byte & (1 << 0)) != 0
    buttons_state["L2"] = (button_byte & (1 << 1)) != 0
    buttons_state["R1"] = (button_byte & (1 << 2)) != 0
    buttons_state["L1"] = (button_byte & (1 << 3)) != 0
    buttons_state["Y"] = (button_byte & (1 << 4)) != 0
    buttons_state["B"] = (button_byte & (1 << 5)) != 0
    buttons_state["X"] = (button_byte & (1 << 6)) != 0
    buttons_state["A"] = (button_byte & (1 << 7)) != 0

    arrows_byte = data[9]
    buttons_state["UP"] = (arrows_byte & (1 << 0)) != 0
    buttons_state["RIGHT"] = (arrows_byte & (1 << 1)) != 0
    buttons_state["LEFT"] = (arrows_byte & (1 << 2)) != 0
    buttons_state["DOWN"] = (arrows_byte & (1 << 3)) != 0
    buttons_state["WINDOW"] = (arrows_byte & (1 << 4)) != 0
    buttons_state["STEAM"] = (arrows_byte & (1 << 5)) != 0
    buttons_state["MENU"] = (arrows_byte & (1 << 6)) != 0
    buttons_state["L5"] = (arrows_byte & (1 << 7)) != 0

    pads_byte = data[10]
    buttons_state["R5"] = (pads_byte & (1 << 0)) != 0
    buttons_state["LEFT_PAD_PRESS"] = (pads_byte & (1 << 1)) != 0
    buttons_state["RIGHT_PAD_PRESS"] = (pads_byte & (1 << 2)) != 0
    buttons_state["LEFT_PAD_TOUCH"] = (pads_byte & (1 << 3)) != 0
    buttons_state["RIGHT_PAD_TOUCH"] = (pads_byte & (1 << 4)) != 0
    buttons_state["LEFT_STICK_PRESS"] = (pads_byte & (1 << 6)) != 0

    sticks1_byte = data[11]
    buttons_state["RIGHT_STICK_PRESS"] = (sticks1_byte & (1 << 2)) != 0

    sticks2_byte = data[13]
    buttons_state["L4"] = (sticks2_byte & (1 << 1)) != 0
    buttons_state["R4"] = (sticks2_byte & (1 << 2)) != 0
    buttons_state["LEFT_STICK_TOUCH"] = (sticks2_byte & (1 << 6)) != 0
    buttons_state["RIGHT_STICK_TOUCH"] = (sticks2_byte & (1 << 7)) != 0

    aux_byte = data[14]
    buttons_state["MORE"] = (aux_byte & (1 << 2)) != 0

    buttons_state["LEFT_STICK_X"] = struct.unpack('<h', data[48:50])[0]
    buttons_state["LEFT_STICK_Y"] = struct.unpack('<h', data[50:52])[0]
    buttons_state["RIGHT_STICK_X"] = struct.unpack('<h', data[52:54])[0]
    buttons_state["RIGHT_STICK_Y"] = struct.unpack('<h', data[54:56])[0]

    buttons_state["LEFT_PAD_X"] = struct.unpack('<h', data[16:18])[0]
    buttons_state["LEFT_PAD_Y"] = struct.unpack('<h', data[18:20])[0]
    buttons_state["RIGHT_PAD_X"] = struct.unpack('<h', data[20:22])[0]
    buttons_state["RIGHT_PAD_Y"] = struct.unpack('<h', data[22:24])[0]

class SteamDeckInput:
    DEVICE_PATHS = ['/dev/input/event5', '/dev/input/event2', '/dev/input/event8', '/dev/input/event14']
    HIDRAW_PATH = '/dev/hidraw2'
    PWR_DEVICE_PATH = '/dev/input/event5'  # The device path for power/volume buttons

    def __init__(self, device_paths=None, hidraw_path=None):
        self.device_paths = device_paths or self.DEVICE_PATHS
        self.hidraw_path = hidraw_path or self.HIDRAW_PATH
        self.general_buttons_state = {}
        self.pwr_buttons_state = {}
        self.listeners = []  # List of callbacks for change events
        self.tasks = []
        self.devices = []

    def add_listener(self, callback):
        """Add a callback to be called on input changes. Callback signature: callback(key, value)"""
        self.listeners.append(callback)

    def on_change(self, key, value):
        """Internal method to trigger listeners on change."""
        for callback in self.listeners:
            callback(key, value)

    async def _read_device_events(self, device_path, buttons_state):
        """Read events from a single device asynchronously."""
        device = None
        try:
            device = InputDevice(device_path)
            device.grab()  # Grab the device to monopolize input
            self.devices.append(device)

            async for event in device.async_read_loop():
                if buttons_state is not None:
                    if event.type == ecodes.EV_KEY:  # Button events
                        key_event = categorize(event)
                        if event.code in [114, 115, 116]:
                            btn_map = {
                                114: "VOLUME_DOWN",
                                115: "VOLUME_UP",
                                116: "POWER"
                            }
                            buttons_state[btn_map[event.code]] = key_event.keystate != 0
        except Exception as e:
            print(f"Error reading ({device_path}): {e}")
        finally:
            if device:
                try:
                    device.ungrab()
                except Exception as e:
                    print(f"Error releasing {device_path}: {e}")

    async def _read_hidraw(self):
        """Read HID raw reports asynchronously."""
        h = None
        try:
            h = hid.Device(path=self.hidraw_path.encode())
            while True:
                data = await asyncio.to_thread(h.read, 64, 5)
                if not data or len(data) < 12:
                    await asyncio.sleep(0.001)
                    continue
                decode_steamdeck_report(data, self.general_buttons_state)
                await asyncio.sleep(0.001)  # Reduced to 1ms to match high report rate
        except hid.HIDException as e:
            print(f"HID error: {e}")
        except Exception as e:
            print(f"Error in read_hidraw: {e}")
        finally:
            if h:
                h.close()

    async def _process_inputs(self):
        """Process input states and detect changes."""
        prev_state = {}
        while True:
            all_buttons_state = {**self.general_buttons_state, **self.pwr_buttons_state}
            for key, val2 in all_buttons_state.items():
                default = 0 if isinstance(val2, (int, float)) else False
                val1 = prev_state.get(key, default)
                if val1 != val2:
                    is_stick = key in ["LEFT_STICK_X", "LEFT_STICK_Y", "RIGHT_STICK_X", "RIGHT_STICK_Y"]
                    is_pad = key in ["LEFT_PAD_X", "LEFT_PAD_Y", "RIGHT_PAD_X", "RIGHT_PAD_Y"]
                    trigger_event = False
                    diff = 0
                    if not isinstance(val2, bool):
                        diff = abs(val2 - val1) 
                        
                    if (not is_stick and not is_pad) or (is_stick and diff>200) or (is_pad and diff>100):
                        self.on_change(key, val2)
                        prev_state[key] = val2

            await asyncio.sleep(0.001)  # Reduced to 1ms to match high report rate

    async def start(self):
        """Start listening to inputs asynchronously."""
        for path in self.device_paths:
            bs = self.pwr_buttons_state if path == self.PWR_DEVICE_PATH else None
            self.tasks.append(self._read_device_events(path, bs))
        self.tasks.append(self._read_hidraw())
        self.tasks.append(self._process_inputs())
        try:
            await asyncio.gather(*self.tasks, return_exceptions=True)
        finally:
            for device in self.devices:
                try:
                    device.ungrab()
                except Exception:
                    pass