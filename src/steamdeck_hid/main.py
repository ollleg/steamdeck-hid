# MIT License

# Copyright (c) 2025 Oleh Polishchuk

import threading
import time
import select
import os
import struct

# Conditional import of evdev (Linux-only)
try:
    import hid
    from evdev import InputDevice, categorize, ecodes, list_devices
    _evdev_available = True
except ImportError:
    _evdev_available = False
    InputDevice = None
    categorize = None
    ecodes = None
    list_devices = None

def is_initialized():
    """Check if evdev is available and the module is properly initialized."""
    return _evdev_available

def list_all_devices():
    """List all available input devices with capabilities."""
    if not _evdev_available:
        print("evdev is not available on this platform (likely macOS/Windows)")
        return []
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
    DEVICE_NAMES = ["Power Button","AT Translated Set 2 keyboard"]  # Populate this list with device names, e.g., ['Steam Deck', 'Valve Software Steam Controller']
    HIDRAW_VID = 0x28de
    HIDRAW_PID = 0x1205

    def __init__(self, device_names=None, hidraw_path=None, polling_interval=0.001):
        if not _evdev_available:
            raise RuntimeError("evdev is not available on this platform. SteamDeckInput requires Linux with evdev support.")
        self.device_names = device_names or self.DEVICE_NAMES
        if not self.device_names:
            raise ValueError("DEVICE_NAMES must be provided or set in the class.")
        self.hidraw_path = hidraw_path or self._find_hidraw_path()
        self.polling_interval = polling_interval  # Interval in seconds
        self.general_buttons_state = {}
        self.pwr_buttons_state = {}
        self.event_queue = []  # List to hold events
        self.lock = threading.Lock()  # Lock for thread-safe access to queue and states
        self.devices = []
        self.threads = []
        self.running = True

        # Start thread for reading evdev devices
        t = threading.Thread(target=self._read_device_events, daemon=True)
        self.threads.append(t)
        t.start()

        t = threading.Thread(target=self._read_hidraw, daemon=True)
        self.threads.append(t)
        t.start()

        t = threading.Thread(target=self._process_inputs, daemon=True)
        self.threads.append(t)
        t.start()

    def _find_hidraw_path(self):
        for device_info in hid.enumerate():
            if device_info['vendor_id'] == self.HIDRAW_VID and device_info['product_id'] == self.HIDRAW_PID and device_info['usage_page'] == 65535:
                path = device_info['path']
                if isinstance(path, bytes):
                    path = path.decode()
                return path
        raise ValueError("Steam Deck HID device not found")

    def get_events(self):
        """Retrieve and clear the list of events since the last call, similar to pygame.event.get()."""
        with self.lock:
            events = self.event_queue[:]
            self.event_queue = []
            return events

    def get_state(self):
        """Retrieve the current state of all controls."""
        with self.lock:
            all_buttons_state = {**self.general_buttons_state, **self.pwr_buttons_state}
            return all_buttons_state.copy()

    def _read_device_events(self):
        """Read events from all devices matching DEVICE_NAMES synchronously."""
        devices = []
        all_paths = list_devices()
        matching_paths = []
        for path in all_paths:
            try:
                dev_check = InputDevice(path)
                if dev_check.name in self.device_names:
                    matching_paths.append(path)
            except Exception as e:
                print(f"Error checking {path}: {e}")
                continue

        for path in matching_paths:
            try:
                dev = InputDevice(path)
                print(f"{dev.name} {path} grabbed")
                dev.grab()  # Grab the device to monopolize input
                devices.append(dev)
            except Exception as e:
                print(f"Error grabbing {path}: {e}")

        with self.lock:
            self.devices.extend(devices)

        while self.running:
            if not devices:
                time.sleep(self.polling_interval)
                continue
            try:
                r, _, _ = select.select([dev.fd for dev in devices], [], [], self.polling_interval)
                if r:
                    for fd in r:
                        for dev in devices[:]:  # Copy to avoid runtime modification
                            if dev.fd == fd:
                                try:
                                    for event in dev.read():
                                        if event.type == ecodes.EV_KEY:  # Button events
                                            key_event = categorize(event)
                                            if event.code in [114, 115, 116]:
                                                btn_map = {
                                                    114: "VOLUME_DOWN",
                                                    115: "VOLUME_UP",
                                                    116: "POWER"
                                                }
                                                with self.lock:
                                                    self.pwr_buttons_state[btn_map[event.code]] = key_event.keystate != 0
                                except Exception as e:
                                    print(f"Error reading {dev.path}: {e}")
                                    devices.remove(dev)
                                    try:
                                        dev.ungrab()
                                    except Exception as ue:
                                        print(f"Error releasing {dev.path}: {ue}")
            except Exception as e:
                print(f"Error in select: {e}")
                # Continue to next iteration

        for dev in devices:
            try:
                dev.ungrab()
            except Exception as e:
                print(f"Error releasing device {dev.path}: {e}")

    def _read_hidraw(self):
        """Read HID raw reports synchronously."""
        h = None
        try:
            h = hid.Device(path=self.hidraw_path.encode())
            while self.running:
                data = h.read(64, timeout=5)
                if data and len(data) >= 12:
                    with self.lock:
                        decode_steamdeck_report(data, self.general_buttons_state)
                time.sleep(self.polling_interval)
        except hid.HIDException as e:
            print(f"HID error: {e}")
        except Exception as e:
            print(f"Error in read_hidraw: {e}")
        finally:
            if h:
                h.close()

    def _process_inputs(self):
        """Process input states and detect changes synchronously."""
        prev_state = {}
        while self.running:
            with self.lock:
                all_buttons_state = {**self.general_buttons_state, **self.pwr_buttons_state}
            for key, val2 in all_buttons_state.items():
                default = 0 if isinstance(val2, (int, float)) else False
                val1 = prev_state.get(key, default)
                if val1 != val2:
                    is_stick = key in ["LEFT_STICK_X", "LEFT_STICK_Y", "RIGHT_STICK_X", "RIGHT_STICK_Y"]
                    is_pad = key in ["LEFT_PAD_X", "LEFT_PAD_Y", "RIGHT_PAD_X", "RIGHT_PAD_Y"]
                    diff = 0
                    if not isinstance(val2, bool):
                        diff = abs(val2 - val1)
                    
                    if (not is_stick and not is_pad) or (is_stick and diff > 200) or (is_pad and diff > 100):
                        with self.lock:
                            self.event_queue.append((key, val2))
                        prev_state[key] = val2
            time.sleep(self.polling_interval)

    def stop(self):
        """Stop all threads and release resources."""
        self.running = False
        for t in self.threads:
            t.join()
        for device in self.devices:
            try:
                device.ungrab()
            except Exception:
                pass