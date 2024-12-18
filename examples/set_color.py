##CODE TO control HUE. Will be included in the library soon


import pylukeroberts as pylr

async def main():
    # try:
    lamp_address = await pylr.find_lamp()
    print(f"Found Luke Roberts Lamp at address: {lamp_address}")
    client = pylr.BleakClient(lamp_address)
    lamp = pylr.LuvoLamp(client)
    # await lamp.update_scenes()
    # await lamp.update_current_scene()
    # print (f'{lamp.get_current_scene()} with ID: {lamp.get_current_scene(True)}')
    await client.connect()
    # tester = await client.read_gatt_char(UNKNOWNONE_UUID)
    # print_bytearray ('UNKNOWNONE_UUID returned: ',tester)
    # await asyncio.sleep(3)
    await client.start_notify(
        char_specifier=CHARACTERISTIC_UUID, callback=print_reply
    )
    hue = 139
    hue_bytes = int((hue / 360) * 65535).to_bytes(byteorder='big',length=2)
    time = 0
    time_bytes = int(time).to_bytes(byteorder='big',length=2) #in ms
    color_temp = 2801
    color_temp_bytes = int(color_temp).to_bytes(byteorder='big',length=2)
    brightness = 10 # 0..255
    brightness_bytes = int(brightness).to_bytes(byteorder='big',length=1)
    saturation = 255 #0..255
    saturation_bytes = int(saturation).to_bytes(byteorder='big',length=1)
    print_bytearray('hue: ',hue_bytes)
    print_bytearray('time: ',time_bytes)
    print_bytearray('brightness: ',brightness_bytes)
    # Downlight                                                 Protocol ----------SetD  DURATION--  Color TEMP  Brightness
    # await client.write_gatt_char(CHARACTERISTIC_UUID, bytearray([0xA0, 0x07, 0x02, 0x02, time_bytes[0], time_bytes[1], color_temp_bytes[0], color_temp_bytes[1], brightness_bytes[0]]), response=True)
    #downlight alternative
    #color temp                                                  Protocol -------  Temp 
    # await client.write_gatt_char(CHARACTERISTIC_UUID, bytearray([0xA0, 0x07, 0x04, 0x0F, 0xA0]), response=True)
    #brightness                                                  Protocol -------  Brightness
    # await client.write_gatt_char(CHARACTERISTIC_UUID, bytearray([0xA0, 0x07, 0x03, 0x30]), response=True)
    #uplight                                                    Protocol ----------SetU  DURATION--  Sat , HUE/ColorT  Brightness
    await client.write_gatt_char(CHARACTERISTIC_UUID, bytearray([0xA0, 0x07, 0x02, 0x01, time_bytes[0], time_bytes[1], saturation_bytes[0], hue_bytes[0], hue_bytes[1], brightness_bytes[0]]), response=True)

    #blink red
    # await client.write_gatt_char(CHARACTERISTIC_UUID, bytearray([0xA0, 0x07, 0x02, 0x01, time_bytes[0], time_bytes[1], 0xFF, hue_bytes[0], hue_bytes[1], 0x30]), response=True)
    #increase brightness
    # await client.write_gatt_char(CHARACTERISTIC_UUID, bytearray([0xA0, 0x07, 0x02, 0x03]), response=True)

    await client.write_gatt_char(CHARACTERISTIC_UUID, bytearray([0x0A]), response=True)
    await asyncio.sleep(1)  # Give time for async operations to complete
    # tester = await client.read_gatt_char(UNKNOWNONE_UUID)
    # print_bytearray ('UNKNOWNONE_UUID returned: ',tester)
    # await client.stop_notify(CHARACTERISTIC_UUID)
    await client.disconnect()


    # await lamp.update_scenes()
    # print(lamp.scenes)
    # await lamp.switch_off()
    # await asyncio.sleep(5)
    # await lamp.switch_on()
    # await get_scenes()
    # print (scenes)
    # await switch_on()
    # await switch_off()
    # except ValueError as ve:
    #     print(ve, file=sys.stderr)
    # except Exception as e:
    #     print(f"An error occurred: {e}", file=sys.stderr)


if __name__ == "__main__":
    asyncio.run(main())