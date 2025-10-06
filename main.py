import time
from steamdeck_hid import SteamDeckInput, list_all_devices

# Optional: List devices to verify paths
list_all_devices()

sdi = SteamDeckInput(
    # Optional parameters
    # device_paths=['/dev/input/event5', '/dev/input/event2', '/dev/input/event8', '/dev/input/event14'],
    # hidraw_path='/dev/hidraw2',
    polling_interval=0.001  # Adjust as needed
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