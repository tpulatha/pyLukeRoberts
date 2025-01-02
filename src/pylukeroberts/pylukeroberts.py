import asyncio
from bleak import BleakScanner, BleakClient
from bleak.backends.device import BLEDevice

SERVICE_UUID = "44092840-0567-11E6-B862-0002A5D5C51B".lower()
CHARACTERISTIC_UUID = "44092842-0567-11E6-B862-0002A5D5C51B".lower()

CURRENTSCENE_UUID = "44092844-0567-11E6-B862-0002A5D5C51B".lower()

UNKNOWNONE_UUID = "44092847-0567-11E6-B862-0002A5D5C51B".lower()
UNKNOWNTWO_UUID = "44092848-0567-11E6-B862-0002A5D5C51B".lower()


def print_bytearray(intro,byte_array: bytearray):
    string = intro
    for byte in byte_array:
        string = string + f"{byte:02x},"
    print (string)

def print_reply(char: str, data: bytearray):
    print_bytearray("Response from request ",data)


async def find_lamp() -> BLEDevice:
    def filter_function(device, advertisement_data):
        # Check if the service UUID is in the advertisement data
        return SERVICE_UUID in advertisement_data.service_uuids

    device = await BleakScanner.find_device_by_filter(
        filter_function,
        timeout=10.0,  # Optional timeout in seconds
    )
    return device

class LUVOLAMP:
    def __init__(self, lamp: BLEDevice):
        self._scenes = []
        self._currentScene = 0
        self._isOn = False
        self._prev_id = 0
        self._client = BleakClient(lamp)

    async def connect(self) -> bool:
        await self.client.connect()
        return True
    
    async def disconnect(self) -> bool:
        await self.client.disconnect()
        return True

    async def switch_off(self) -> bool:
        #scene 0x00 is switch off
        await self.select_scene(0x00)
        return True

    async def switch_on(self) -> bool:
        #scene 0xFF is switch on with default scene
        await self.select_scene(0xFF)
        return True

    async def select_scene(self, scene_id: int) -> bool:
        try:
            await self._client.connect()
            command = bytearray([0xA0, 0x02, 0x05, scene_id])
            await self._client.write_gatt_char(
                char_specifier=CHARACTERISTIC_UUID, data=command, response=True
            )
            if scene_id == 0x00:
                self._isOn = False
            else:
                self._isOn = True
        finally:
            await self._client.disconnect()
        return True

    async def update_scenes(self) -> bool:
        result = await self._client.connect()
        await self._client.start_notify(
            char_specifier=CHARACTERISTIC_UUID, callback=self._get_scene_names
        )
        print(f"Connected to the lamp: {result}")
        #Defining a custom bytearray to indicate initial call to function
        command = bytearray([0x00, 0x00, 0x00, 0x00])
        try:
            await self._get_scene_names(char=CHARACTERISTIC_UUID, data=command)
        finally:
            await self._client.disconnect()
        return True

    async def _get_scene_names(self,char: str, data: bytearray):
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

    async def update_current_scene(self) -> bool:
        await self._client.connect()
        result = await self._client.read_gatt_char(CURRENTSCENE_UUID) 
        self._currentScene = int.from_bytes(result,byteorder='big',signed=False)
        await self._client.disconnect()
        return True
    
    def get_current_scene(self,getID: bool = False) -> int | str:
        if getID:
            return self._currentScene
        else:
            for scene in self._scenes:
                if scene['id'] == self._currentScene:
                    return scene['name']

