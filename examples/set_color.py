from pylukeroberts import LuvoLamp, find_lamp
import asyncio


async def main():
    device = await find_lamp()
    if device is None:
        print("No Luke Roberts lamp found")
        return
    print(f"Found Luke Roberts Lamp at address: {device.address}")
    lamp = LuvoLamp(device)

    # Set the uplight color (Hue: 139 degrees, Saturation: 100%, Brightness: 4%)
    await lamp.set_hue(hue=139, saturation=100, brightness=4)

    # Set the downlight color temperature to 3000 K
    await lamp.set_color_temperature(3000)


if __name__ == "__main__":
    asyncio.run(main())
