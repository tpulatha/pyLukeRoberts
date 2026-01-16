from pylukeroberts import LUVOLAMP, find_lamp
import asyncio

async def main():
    lamp_address = await find_lamp()
    print(f"Found Luke Roberts Lamp at address: {lamp_address}")
    
    lamp = LUVOLAMP(lamp_address)
    
    # Set the color (Hue: 139 degrees, Saturation: 100%, Brightness: ~4%)
    # The original example used raw brightness 10/255, which corresponds to approx 4%.
    await lamp.set_hue(hue=139, saturation=100, brightness=4)

if __name__ == "__main__":
    asyncio.run(main())