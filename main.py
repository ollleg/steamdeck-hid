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