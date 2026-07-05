from pylukeroberts import LuvoLamp, find_lamp
import asyncio


async def main():
    device = await find_lamp()
    if device is None:
        print("No Luke Roberts lamp found")
        return
    print(f"Found Luke Roberts Lamp at address: {device.address}")
    lamp = LuvoLamp(device)
    await lamp.update_scenes()
    await lamp.update_current_scene()
    print(f"{lamp.current_scene_name} with ID: {lamp.current_scene_id}")
    await lamp.select_scene(12)
    await lamp.switch_off()


if __name__ == "__main__":
    asyncio.run(main())
