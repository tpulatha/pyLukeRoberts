from pylukeroberts import LuvoLamp, find_lamp
import asyncio


async def main():
    device = await find_lamp()
    if device is None:
        print("No Luke Roberts lamp found")
        return
    print(f"Found Luke Roberts Lamp at address: {device.address}")
    lamp = LuvoLamp(device)
    await lamp.set_brightness(20)
    await asyncio.sleep(4)
    await lamp.set_relative_brightness(60)
    await asyncio.sleep(4)
    await lamp.set_relative_brightness(-40)


if __name__ == "__main__":
    asyncio.run(main())
