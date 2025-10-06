import asyncio
from steamdeck import SteamDeckInput, list_all_devices

# Optionally list devices to verify paths
# list_all_devices()

async def main():
    sdi = SteamDeckInput()  # Use default paths, or pass custom: SteamDeckInput(device_paths=['/dev/input/eventX', ...], hidraw_path='/dev/hidrawY')

    def my_callback(key, value):
        print(f"Event: '{key}' changed to {value}")

    sdi.add_listener(my_callback)

    await sdi.start()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Program terminated by user")
    except Exception as e:
        print(f"Error: {e}")