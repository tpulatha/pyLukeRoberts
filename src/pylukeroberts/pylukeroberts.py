from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass

from bleak import BleakScanner, BleakClient, BLEDevice, AdvertisementData

from .const import (
    SERVICE_UUID,
    CHARACTERISTIC_UUID,
    CURRENTSCENE_UUID,
    COMMAND_PREFIX,
    API_V1,
    API_V2,
    OPCODE_QUERY_SCENE,
    OPCODE_IMMEDIATE_LIGHT,
    OPCODE_BRIGHTNESS,
    OPCODE_COLOR_TEMPERATURE,
    OPCODE_SELECT_SCENE,
    OPCODE_RELATIVE_BRIGHTNESS,
    IMMEDIATE_LIGHT_UPLIGHT,
    SCENE_OFF,
    SCENE_DEFAULT,
    SCENE_LIST_END,
    STATUS_OK,
    MIN_KELVIN,
    MAX_KELVIN,
)

_LOGGER = logging.getLogger(__name__)

SCENE_LIST_TIMEOUT = 30.0


@dataclass(frozen=True)
class Scene:
    """A light scene configured on the lamp."""

    id: int
    name: str


async def find_lamp(timeout: float = 10.0) -> BLEDevice | None:
    """Scan for the first lamp advertising the Luke Roberts control service.

    Returns None if no lamp is found within ``timeout`` seconds.
    """

    def filter_function(
        device: BLEDevice, advertisement_data: AdvertisementData
    ) -> bool:
        return SERVICE_UUID in advertisement_data.service_uuids

    return await BleakScanner.find_device_by_filter(
        filter_function,
        timeout=timeout,
        service_uuids=[SERVICE_UUID],
    )


def hue_to_bytes(hue: float) -> bytes:
    """Convert a hue in degrees (0-360) to the 16-bit wire format (0-65535)."""
    if not 0 <= hue <= 360:
        raise ValueError("Hue value must be between 0 and 360 degrees.")
    return as_bytes(int((hue / 360) * 65535))


def as_bytes(value: int) -> bytes:
    return value.to_bytes(length=2, byteorder="big")


def percent_as_byte(value: int) -> bytes:
    """Scale a percentage (0-100) to a single byte (0-255)."""
    if not 0 <= value <= 100:
        raise ValueError("Percentage value must be between 0 and 100.")
    return int((value / 100) * 255).to_bytes(length=1, byteorder="big")


class LuvoLamp:
    """Control a Luke Roberts Luvo lamp over Bluetooth Low Energy.

    Lamps terminate connections after 8 seconds of inactivity, so every
    command opens a short-lived connection and disconnects afterwards.
    """

    def __init__(
        self,
        lamp: BLEDevice,
        advertisement_data: AdvertisementData | None = None,
    ) -> None:
        """Initialize the lamp object"""
        self._scenes: list[Scene] = []
        self._current_scene: int = SCENE_OFF
        self._is_on: bool = False
        self._ble_device = lamp
        self._client = BleakClient(lamp)
        self._advertisement_data = advertisement_data

    @property
    def address(self) -> str:
        """Bluetooth address of the lamp."""
        return self._client.address

    @property
    def is_on(self) -> bool:
        """Whether the lamp is on, based on the last known scene."""
        return self._is_on

    @property
    def scenes(self) -> list[Scene]:
        """Scenes read from the lamp by the last update_scenes() call."""
        return list(self._scenes)

    @property
    def current_scene_id(self) -> int:
        """Id of the current scene, as of the last update_current_scene()."""
        return self._current_scene

    @property
    def current_scene_name(self) -> str | None:
        """Name of the current scene, or None if it is not in the scene list."""
        for scene in self._scenes:
            if scene.id == self._current_scene:
                return scene.name
        return None

    def set_ble_device_and_advertisement_data(
        self, lamp: BLEDevice, advertisement_data: AdvertisementData
    ) -> None:
        """Set the ble device."""
        self._ble_device = lamp
        self._advertisement_data = advertisement_data
        if not self._client.is_connected:
            self._client = BleakClient(lamp)

    async def connect(self) -> None:
        """Connect to the lamp"""
        _LOGGER.debug("Connecting to the lamp [%s]", self._client.address)
        await self._client.connect()

    async def disconnect(self) -> None:
        """Disconnect from the lamp"""
        _LOGGER.debug("Disconnecting the lamp [%s]", self._client.address)
        await self._client.disconnect()

    async def _send_command(self, command: bytes) -> None:
        """Connect, write a command to the external API endpoint, disconnect."""
        try:
            await self._client.connect()
            _LOGGER.debug(
                "Sending %s to [%s]", command.hex(","), self._client.address
            )
            await self._client.write_gatt_char(
                char_specifier=CHARACTERISTIC_UUID, data=command, response=True
            )
        finally:
            await self._client.disconnect()

    async def switch_off(self) -> None:
        """Switch off the lamp"""
        _LOGGER.debug("Switching off Lamp [%s]", self._client.address)
        await self.select_scene(SCENE_OFF)

    async def switch_on(self) -> None:
        """Switch on the lamp with the default scene"""
        _LOGGER.debug("Switching on Lamp [%s]", self._client.address)
        await self.select_scene(SCENE_DEFAULT)

    async def update(self) -> None:
        """Refresh lamp state: scene list (first call only) and current scene."""
        if not self._scenes:
            await self.update_scenes()
        await self.update_current_scene()

    async def stop(self) -> None:
        """Disconnect from the lamp if a connection is open."""
        if self._client.is_connected:
            await self._client.disconnect()

    async def select_scene(self, scene_id: int) -> None:
        """Select a scene on the lamp"""
        if not 0 <= scene_id <= 0xFF:
            raise ValueError("Scene id must be between 0 and 255.")
        _LOGGER.debug(
            "Selecting scene %s [%s]", scene_id, self._client.address
        )
        await self._send_command(
            bytes([COMMAND_PREFIX, API_V2, OPCODE_SELECT_SCENE, scene_id])
        )
        self._is_on = scene_id != SCENE_OFF
        if scene_id != SCENE_DEFAULT:
            self._current_scene = scene_id

    async def set_hue(
        self, hue: int, saturation: int, brightness: int, duration_ms: int = 0
    ) -> None:
        """Set the uplight color as HSB, optionally reverting after duration_ms.

        The change modifies the current scene and is lost on power-down.
        """
        if not 0 <= duration_ms <= 0xFFFF:
            raise ValueError("Duration must be between 0 and 65535 ms.")
        duration = as_bytes(duration_ms)
        hue_b = hue_to_bytes(hue)
        saturation_b = percent_as_byte(saturation)
        brightness_b = percent_as_byte(brightness)
        _LOGGER.debug(
            "Setting hsb %s-%s-%s on [%s]",
            hue,
            saturation,
            brightness,
            self._client.address,
        )
        await self._send_command(
            bytes(
                [
                    COMMAND_PREFIX,
                    API_V1,
                    OPCODE_IMMEDIATE_LIGHT,
                    IMMEDIATE_LIGHT_UPLIGHT,
                    duration[0],
                    duration[1],
                    saturation_b[0],
                    hue_b[0],
                    hue_b[1],
                    brightness_b[0],
                ]
            )
        )

    async def set_color_temperature(self, kelvin: int) -> None:
        """Set the downlight color temperature of the current scene in Kelvin."""
        if not MIN_KELVIN <= kelvin <= MAX_KELVIN:
            raise ValueError(
                f"Color temperature must be between {MIN_KELVIN} and {MAX_KELVIN} K."
            )
        kelvin_b = as_bytes(kelvin)
        _LOGGER.debug(
            "Setting color temperature %sK on [%s]", kelvin, self._client.address
        )
        await self._send_command(
            bytes(
                [
                    COMMAND_PREFIX,
                    API_V1,
                    OPCODE_COLOR_TEMPERATURE,
                    kelvin_b[0],
                    kelvin_b[1],
                ]
            )
        )

    async def update_scenes(self) -> None:
        """Read the list of configured scenes from the lamp.

        Replaces the cached scene list available via the ``scenes`` property.
        """
        scenes: list[Scene] = []
        done = asyncio.Event()
        queried_id = SCENE_OFF
        error: int | None = None

        async def _on_scene_response(char: str, data: bytearray) -> None:
            nonlocal queried_id, error
            status = data[0]
            if status != STATUS_OK:
                error = status
                done.set()
                return
            next_id = data[2]
            name = bytes(data[3:]).decode("utf-8").rstrip("\x00")
            scenes.append(Scene(id=queried_id, name=name))
            _LOGGER.debug(
                "Scene id %s name %s (next id 0x%02x)", queried_id, name, next_id
            )
            if next_id == SCENE_LIST_END:
                done.set()
                return
            queried_id = next_id
            await self._client.write_gatt_char(
                char_specifier=CHARACTERISTIC_UUID,
                data=bytes([COMMAND_PREFIX, API_V1, OPCODE_QUERY_SCENE, next_id]),
                response=True,
            )

        try:
            await self._client.connect()
            _LOGGER.debug("Read scenes from Lamp [%s]", self._client.address)
            await self._client.start_notify(
                char_specifier=CHARACTERISTIC_UUID, callback=_on_scene_response
            )
            await self._client.write_gatt_char(
                char_specifier=CHARACTERISTIC_UUID,
                data=bytes([COMMAND_PREFIX, API_V1, OPCODE_QUERY_SCENE, queried_id]),
                response=True,
            )
            await asyncio.wait_for(done.wait(), timeout=SCENE_LIST_TIMEOUT)
        finally:
            await self._client.disconnect()
        if error is not None:
            raise RuntimeError(
                f"Scene query rejected by lamp with status 0x{error:02x}"
            )
        self._scenes = scenes

    async def update_current_scene(self) -> None:
        """Read the current set scene from the lamp"""
        _LOGGER.debug("Read current scene from Lamp [%s]", self._client.address)
        try:
            await self._client.connect()
            result = await self._client.read_gatt_char(CURRENTSCENE_UUID)
            self._current_scene = int.from_bytes(
                result, byteorder="big", signed=False
            )
            self._is_on = self._current_scene != SCENE_OFF
        finally:
            await self._client.disconnect()

    def get_current_scene(self, getid: bool = False) -> int | str:
        """Get the current scene id or name.

        Deprecated: use the ``current_scene_id`` and ``current_scene_name``
        properties instead.
        """
        if getid:
            return self._current_scene
        name = self.current_scene_name
        if name is None:
            raise ValueError(
                f"Scene ID {self._current_scene} not found in scene list."
            )
        return name

    async def set_brightness(self, brightness: int) -> None:
        """Set the brightness of the current scene in percent (0-100)."""
        if not 0 <= brightness <= 100:
            raise ValueError("Percentage value must be between 0 and 100.")
        _LOGGER.debug(
            "Setting brightness %s%% on [%s]", brightness, self._client.address
        )
        await self._send_command(
            bytes([COMMAND_PREFIX, API_V1, OPCODE_BRIGHTNESS, brightness])
        )

    async def set_relative_brightness(self, brightness: int) -> None:
        """Adjust the brightness of the current scene by a relative percentage.

        Values between -100 and 100; the lamp clamps the result to 0-100%.
        """
        if not -100 <= brightness <= 100:
            raise ValueError("Percentage value must be between -100 and 100.")
        _LOGGER.debug(
            "Adjusting brightness by %s%% on [%s]", brightness, self._client.address
        )
        await self._send_command(
            bytes([COMMAND_PREFIX, API_V2, OPCODE_RELATIVE_BRIGHTNESS])
            + brightness.to_bytes(length=1, byteorder="big", signed=True)
        )


# Backwards-compatible alias for the pre-0.5.0 class name.
LUVOLAMP = LuvoLamp
