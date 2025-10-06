# MIT License
# Copyright (c) 2025 Oleh Polishchuk

import asyncio
from evdev import InputDevice, categorize, ecodes, list_devices
import os
import struct
import hid

# Device paths (replace if needed based on evtest or device listing)
DEVICE_PATHS = ['/dev/input/event5', '/dev/input/event2', '/dev/input/event8', '/dev/input/event14']
HIDRAW_PATH = '/dev/hidraw2'

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

async def read_device_events(device_path, buttons_state):
    """Read events from a single device asynchronously with verbose debugging."""
    device = None
    try:
        device = InputDevice(device_path)
        device.grab()  # Grab the device to monopolize input
        print(f"Connected to {device_path}: {device.name}")

        async for event in device.async_read_loop():
            if buttons_state is not None:
                if event.type == ecodes.EV_KEY:  # Button events
                    key_event = categorize(event)
                    #state = "pressed" if key_event.keystate == 1 else "released" if key_event.keystate == 0 else "held"
                    #print(f"{device_path}: Button {key_event.keycode} {state} (code: {event.code})")
                    if event.code in [114, 115, 116]:
                        btn_map = {
                            114: "VOLUME_DOWN",
                            115: "VOLUME_UP",
                            116: "POWER"
                        }
                        buttons_state[btn_map[event.code]] = False if key_event.keystate == 0 else True
                elif event.type == ecodes.EV_ABS:  # Analog sticks, triggers, etc.
                    abs_event = categorize(event)
                    print(f"{device_path}: Axis {ecodes.ABS[abs_event.event.code]} (code: {abs_event.event.code}) value: {abs_event.event.value}")
                elif event.type == ecodes.EV_REL:  # Relative events
                    print(f"{device_path}: Relative event {event.code} value: {event.value}")
    except Exception as e:
        print(f"Error reading ({device_path}): {e}")
    finally:
        if device:
            try:
                device.ungrab()  # Release the device
                print(f"Released {device_path}: {device.name}")
            except Exception as e:
                print(f"Error releasing {device_path}: {e}")

def decode_steamdeck_report(data, buttons_state : dict):
    """Decode a Steam Deck HID report for buttons and axes."""
    if len(data) < 12:  # Adjust based on actual report size
        return "Invalid report size"

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

    data_int = int.from_bytes(data[16:20], 'big')
    #print(f'{data_int:0{8}x} {buttons_state["LEFT_STICK_X"]}')
    #print(f'{buttons_state["LEFT_STICK_X"]} {buttons_state["LEFT_STICK_Y"]} {buttons_state["RIGHT_STICK_X"]} {buttons_state["RIGHT_STICK_Y"]}')
    l_trigger = data[10]
    r_trigger = data[11]

    return buttons_state

def state_to_str(buttons):
    output = []
    for btn, state in buttons.items():
        if state:
            output.append(f"Button {btn}: Pressed")
    # output.append(f"Left Stick X: {left_stick_x}, Y: {left_stick_y}")
    # output.append(f"Right Stick X: {right_stick_x}, Y: {right_stick_y}")
    # output.append(f"Left Trigger: {l_trigger}")
    # output.append(f"Right Trigger: {r_trigger}")
    return "\n".join(output) if output else None

async def read_hidraw(buttons_state):
    try:
        with hid.Device(path=HIDRAW_PATH.encode()) as h:
            print(f"Connected to hidraw device: {h.manufacturer} {h.product}")
            print(f"Report descriptor: {h.get_report_descriptor().hex()}")

            prev_report = None
            while True:
                data = await asyncio.to_thread(h.read, 64, 5)

                                         
                mask_hex = bytes.fromhex("00000000000000FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF0000000000000000000000000000000000000000FFFFFFFF0000000000000000FFFFFFFF00000000")
                mask_int = int.from_bytes(mask_hex, 'big')
                data_int = int.from_bytes(data, 'big')
                
                #print(f"\nRaw HID report: \n{data_int:0{128}x} \n{(data_int & mask_int):0{128}x}")
                decode_steamdeck_report(data, buttons_state)
                prev_report = data
                await asyncio.sleep(0.001)  # Reduced to 1ms to match high report rate
    except hid.HIDException as e:
        print(f"HID error: {e}")
    except Exception as e:
        print(f"Error in read_hidraw: {e}")

async def process_inputs(general_buttons_state, pwr_buttons_state):
    prev_buttons_state = {}
    while True:
        all_buttons_state = {**general_buttons_state, **pwr_buttons_state}
        decoded = state_to_str(all_buttons_state)
        # if decoded:
        #     print(f"Decoded: {decoded}")

        for key in all_buttons_state.keys():
            val1 = prev_buttons_state.get(key, False)  # Default to False if missing
            val2 = all_buttons_state.get(key, False)
            is_sticks_val = key in ["LEFT_STICK_X", "LEFT_STICK_Y", "RIGHT_STICK_X", "RIGHT_STICK_Y"]
            is_pads_val = key in ["LEFT_PAD_X", "LEFT_PAD_Y", "RIGHT_PAD_X", "RIGHT_PAD_Y"]
            if val1 != val2:
                if (not is_sticks_val and not is_pads_val) or (is_sticks_val and abs(val2-val1)>200) or (is_pads_val and abs(val2-val1)>100):
                    print(f"Event: '{key}' changed to {val2}")
                    prev_buttons_state[key] = val2

        await asyncio.sleep(0.001)  # Reduced to 1ms to match high report rate

async def main():
    list_all_devices()
    tasks = []
    devices = []
    buttons_state = {}
    pwr_buttons_state = {}
    for i, path in enumerate(DEVICE_PATHS):
        if path == '/dev/input/event5':
            tasks.append(read_device_events(path, pwr_buttons_state))
        else:
            tasks.append(read_device_events(path, None))
        try:
            devices.append(InputDevice(path))
        except Exception as e:
            print(f"Failed to initialize {path}: {e}")
    
    tasks.append(read_hidraw(buttons_state))
    tasks.append(process_inputs(buttons_state, pwr_buttons_state))

    try:
        await asyncio.gather(*tasks, return_exceptions=True)
    finally:
        for i, device in enumerate(devices):
            try:
                device.ungrab()
                print(f"Released Device {i+1} ({device.path}): {device.name}")
            except Exception:
                pass

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Program terminated by user")
    except Exception as e:
        print(f"Error: {e}")
