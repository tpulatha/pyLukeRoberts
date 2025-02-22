from __future__ import annotations
from typing import Optional, Union, List, Dict

import asyncio
import logging

from bleak.backends.device import BLEDevice
from bleak.backends.scanner import AdvertisementData
from bleak import BleakScanner, BleakClient


from .const import (
    SERVICE_UUID,
    CHARACTERISTIC_UUID,
    CURRENTSCENE_UUID,
)

_LOGGER = logging.getLogger(__name__)

#Helper
def print_bytearray(intro,byte_array: bytearray) -> None:
    '''Prints a bytearray in a human readable format'''
    string = intro
    for byte in byte_array:
        string = string + f"{byte:02x},"
    print (string)

def print_reply(char: str, data: bytearray) -> None:
    '''Prints the response from the lamp'''
    print_bytearray("Response from request ",data)


async def find_lamp() -> BLEDevice:
    '''Find the lamp using the service UUID'''
    def filter_function(device:BLEDevice,advertisement_data: AdvertisementData) -> BLEDevice:
        '''Filter function to find the lamp'''
        return SERVICE_UUID in advertisement_data.service_uuids

    device = await BleakScanner.find_device_by_filter(
        filter_function,
    )
    return device

def hue_to_bytes(hue: float) -> bytearray:
    if not (0 <= hue <= 360):
        raise ValueError("Hue value must be between 0 and 360 degrees.")
    hue_int = int((hue / 360) * 65535)
    return as_bytes(hue_int)

def as_bytes(value: int) -> bytearray:
    return value.to_bytes(byteorder='big', length=2)

def percent_as_byte(value: int) -> bytearray:
    if not (0 <= value <= 100):
        raise ValueError("Percentage value must be between 0 and 100.")
    value = int((value / 100) * 255)
    return int(value).to_bytes(byteorder='big', length=1)

class LUVOLAMP:
    def __init__(
        self, 
        lamp: BLEDevice, 
        advertisement_data: Optional[AdvertisementData] = None
    ) -> None:
        '''Initialise the lamp object'''
        self._scenes: List[Dict[str, Union[int, str]]] = []
        self._currentScene: int = 0
        self._isOn: bool = False
        self._prev_id: int = 0
        self._ble_device = lamp
        self._client = BleakClient(lamp)
        self._advertisement_data = advertisement_data

    def set_ble_device_and_advertisement_data(
        self, lamp: BLEDevice, advertisement_data: AdvertisementData
    ) -> None:
        """Set the ble device."""
        self._ble_device = lamp
        self._advertisement_data = advertisement_data

    async def connect(self) -> None:
        '''Connect to the lamp'''
        _LOGGER.debug(f"Connecting to the lamp [{self._client.address}]")
        await self._client.connect()
    
    async def disconnect(self) -> None:
        '''Disconnect from the lamp'''
        _LOGGER.debug(f"Disconnecting the lamp [{self._client.address}]")
        await self._client.disconnect()

    async def switch_off(self) -> None:
        '''Switch off the lamp'''
        _LOGGER.debug(f"Switching off Lamp [{self._client.address}]")
        #scene 0x00 is switch off
        await self.select_scene(0x00)

    async def switch_on(self) -> None:
        '''Switch on the lamp'''
        _LOGGER.debug(f"Switching on Lamp [{self._client.address}]")
        #scene 0xFF is switch on with default scene
        await self.select_scene(0xFF)


    async def update(self) -> None:
        '''Update the lamp -- Stub will be implemented later'''
        pass

    async def stop(self):
        '''Stop the lamp -- Stub will be implemented later'''
        pass

    async def select_scene(self, scene_id: int) -> None:
        '''Select a scene on the lamp'''
        try:
            await self._client.connect()
            command = bytearray([0xA0, 0x02, 0x05, scene_id])
            _LOGGER.debug(f"Selecting scene {scene_id} [{self._client.address}]")
            await self._client.write_gatt_char(
                char_specifier=CHARACTERISTIC_UUID, data=command, response=True
            )
            if scene_id == 0x00:
                self._isOn = False
            else:
                self._isOn = True
        finally:
            await self._client.disconnect()
            
    async def set_hue(self, hue: int, saturation: int, brightness: int) -> None:
        '''Set the lamps hue'''
        try:
            await self._client.connect()
            time = as_bytes(0)
            hue_b = hue_to_bytes(hue)
            saturation_b = percent_as_byte(saturation)
            brightness_b= percent_as_byte(brightness)
            command = bytearray([0xA0, 0x07, 0x02, 0x01, time[0], time[1], saturation_b[0], hue_b[0], hue_b[1], brightness_b[0]])
            _LOGGER.debug(f"Setting hsb {hue}-{saturation}-{brightness} on [{self._client.address}]")
            await self._client.write_gatt_char(
                char_specifier=CHARACTERISTIC_UUID, data=command, response=True
            )
        finally:
            await self._client.disconnect()

    async def update_scenes(self) -> None:
        '''Read scenes from Lamp'''
        await self._client.connect()
        _LOGGER.debug(f"Read scenes from Lamp [{self._client.address}]")
        await self._client.start_notify(
            char_specifier=CHARACTERISTIC_UUID, callback=self._get_scene_names
        )
        #Defining a custom bytearray to indicate initial call to function
        command = bytearray([0x00, 0x00, 0x00, 0x00])
        try:
            await self._get_scene_names(char=CHARACTERISTIC_UUID, data=command)
        finally:
            await self._client.disconnect()

    async def _get_scene_names(self,char: str, data: bytearray) -> None:
        '''Get the scene names from the lamp internal function'''
        # print (f'--> Response: {data} for {char}')
        if data[2] == 0x00:
            print("Initial query")
            self._prev_id = 0
            # first query
            command = bytearray([0xA0, 0x01, 0x01, 0x00])
            # print (f'Calling next request with: {command}')
            await self._client.write_gatt_char(
                char_specifier=CHARACTERISTIC_UUID, data=command, response=True
            )
            await asyncio.sleep(1)  # Give time for async operations to complete
        elif data[2] == 0xFF:
            scene_name = data[3:].decode("utf-8").lstrip("\x00")
            self._scenes.append({"id": self._prev_id, "name": scene_name})
            print(f"Returned scene id: {self._prev_id} Name: {scene_name}")
            print("Finish")
        else:
            scene_name = data[3:].decode("utf-8").lstrip("\x00")
            self._scenes.append({"id": self._prev_id, "name": scene_name})
            print(f"Returned scene id: {self._prev_id} Name: {scene_name}")
            # print ("Resuming requests")
            self._prev_id = data[2]
            command = bytearray([0xA0, 0x01, 0x01, data[2]])
            # print (f'Calling next request with: {command}')
            await self._client.write_gatt_char(
                char_specifier=CHARACTERISTIC_UUID, data=command, response=True
            )
            await asyncio.sleep(1)  # Give time for async operations to complete

    async def update_current_scene(self) -> None:
        '''Read the current set scene from the lamp'''
        _LOGGER.debug(f"Read current scene from Lamp [{self._client.address}]")
        await self._client.connect()
        result = await self._client.read_gatt_char(CURRENTSCENE_UUID) 
        self._currentScene = int.from_bytes(result,byteorder='big',signed=False)
        await self._client.disconnect()
    
    def get_current_scene(self,getID: bool = False) -> int | str:
        '''Get the current scene ID or name from the lamp'''
        _LOGGER.debug(f"Get current scene from Lamp [{self._client.address}]")
        if getID:
            return self._currentScene
        else:
            for scene in self._scenes:
                if scene['id'] == self._currentScene:
                    return scene['name']

