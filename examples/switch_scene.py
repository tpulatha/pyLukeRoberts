from pylukeroberts import LUVOLAMP, find_lamp
import asyncio

async def main():
    # try:
    lamp_address = await find_lamp()
    print(f"Found Luke Roberts Lamp at address: {lamp_address}")
    lamp = LUVOLAMP(lamp_address)
    await lamp.update_scenes()
    await lamp.update_current_scene()
    print (f'{lamp.get_current_scene()} with ID: {lamp.get_current_scene(True)}')
    await lamp.select_scene(12)
    await lamp.switch_off()

if __name__ == "__main__":
    asyncio.run(main())