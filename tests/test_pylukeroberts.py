"""Byte-level tests for the Luke Roberts BLE protocol implementation.

Every expected command is taken verbatim from docs/LR BT API v1.6.pdf.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from pylukeroberts import LUVOLAMP, LuvoLamp, Scene, find_lamp
from pylukeroberts.const import CHARACTERISTIC_UUID, CURRENTSCENE_UUID
from pylukeroberts.pylukeroberts import as_bytes, hue_to_bytes, percent_as_byte


@pytest.fixture
def client():
    client = MagicMock()
    client.address = "AA:BB:CC:DD:EE:FF"
    client.is_connected = True
    client.connect = AsyncMock()
    client.disconnect = AsyncMock()
    client.write_gatt_char = AsyncMock()
    client.read_gatt_char = AsyncMock()
    client.start_notify = AsyncMock()
    client.stop_notify = AsyncMock()
    return client


@pytest.fixture
def lamp(client):
    with patch(
        "pylukeroberts.pylukeroberts.establish_connection",
        new=AsyncMock(return_value=client),
    ) as establish:
        device = MagicMock()
        device.address = "AA:BB:CC:DD:EE:FF"
        device.name = "Luvo"
        lamp = LuvoLamp(device)
        lamp.establish_mock = establish
        yield lamp


def written_commands(client) -> list[bytes]:
    return [
        bytes(call.kwargs["data"])
        for call in client.write_gatt_char.call_args_list
    ]


# --- helpers ---------------------------------------------------------------


def test_hue_to_bytes_range():
    assert hue_to_bytes(0) == b"\x00\x00"
    assert hue_to_bytes(360) == b"\xff\xff"
    with pytest.raises(ValueError):
        hue_to_bytes(361)
    with pytest.raises(ValueError):
        hue_to_bytes(-1)


def test_percent_as_byte_range():
    assert percent_as_byte(0) == b"\x00"
    assert percent_as_byte(100) == b"\xff"
    with pytest.raises(ValueError):
        percent_as_byte(101)
    with pytest.raises(ValueError):
        percent_as_byte(-1)


def test_as_bytes_is_big_endian():
    assert as_bytes(0x62D7) == b"\x62\xd7"


def test_luvolamp_alias():
    assert LUVOLAMP is LuvoLamp


# --- connection management ---------------------------------------------------


async def test_connection_is_reused_between_commands(lamp, client):
    await lamp.set_brightness(10)
    await lamp.set_brightness(20)
    lamp.establish_mock.assert_awaited_once()
    client.disconnect.assert_not_awaited()
    assert lamp.is_connected


async def test_idle_timer_armed_after_command(lamp, client):
    await lamp.set_brightness(10)
    assert lamp._disconnect_timer is not None


async def test_stop_disconnects_and_cancels_timer(lamp, client):
    await lamp.set_brightness(10)
    await lamp.stop()
    client.disconnect.assert_awaited_once()
    assert lamp._disconnect_timer is None
    assert not lamp.is_connected


async def test_reconnects_after_external_disconnect(lamp, client):
    await lamp.set_brightness(10)
    # simulate the lamp dropping the connection (8s inactivity timeout)
    lamp._handle_disconnect(client)
    assert not lamp.is_connected
    await lamp.set_brightness(20)
    assert lamp.establish_mock.await_count == 2


async def test_disconnects_after_write_failure(lamp, client):
    client.write_gatt_char.side_effect = OSError("gatt error")
    with pytest.raises(OSError):
        await lamp.set_brightness(10)
    client.disconnect.assert_awaited_once()
    assert not lamp.is_connected


# --- commands on the wire ----------------------------------------------------


async def test_select_scene(lamp, client):
    await lamp.select_scene(12)
    # 05 Select Scene: A0 02 05 II
    assert written_commands(client) == [bytes([0xA0, 0x02, 0x05, 12])]
    assert lamp.is_on
    assert lamp.current_scene_id == 12


async def test_switch_off_and_on(lamp, client):
    await lamp.switch_off()
    assert not lamp.is_on
    await lamp.switch_on()
    assert lamp.is_on
    assert written_commands(client) == [
        bytes([0xA0, 0x02, 0x05, 0x00]),
        bytes([0xA0, 0x02, 0x05, 0xFF]),
    ]


async def test_select_scene_invalid_id_does_not_connect(lamp):
    with pytest.raises(ValueError):
        await lamp.select_scene(256)
    lamp.establish_mock.assert_not_awaited()


async def test_set_brightness_sends_raw_percent(lamp, client):
    await lamp.set_brightness(50)
    await lamp.set_brightness(100)
    # 03 Modify Brightness: A0 01 03 PP with PP in percent 0..100
    assert written_commands(client) == [
        bytes([0xA0, 0x01, 0x03, 50]),
        bytes([0xA0, 0x01, 0x03, 100]),
    ]


async def test_set_brightness_invalid_does_not_connect(lamp):
    with pytest.raises(ValueError):
        await lamp.set_brightness(150)
    lamp.establish_mock.assert_not_awaited()


async def test_set_relative_brightness_uses_v2_and_twos_complement(lamp, client):
    await lamp.set_relative_brightness(-40)
    await lamp.set_relative_brightness(60)
    # 08 Relative Brightness: A0 02 08 PP with PP as 8-bit two's complement
    assert written_commands(client) == [
        bytes([0xA0, 0x02, 0x08, 0xD8]),
        bytes([0xA0, 0x02, 0x08, 60]),
    ]


async def test_set_relative_brightness_invalid_does_not_connect(lamp):
    with pytest.raises(ValueError):
        await lamp.set_relative_brightness(-101)
    lamp.establish_mock.assert_not_awaited()


async def test_set_hue(lamp, client):
    await lamp.set_hue(hue=139, saturation=100, brightness=4)
    # 02 Immediate Light: A0 01 02 XX DD DD SS HH HH BB
    # hue 139 deg -> int(139 / 360 * 65535) = 25303 = 0x62D7
    # saturation 100% -> 255, brightness 4% -> 10, duration 0
    assert written_commands(client) == [
        bytes([0xA0, 0x01, 0x02, 0x01, 0x00, 0x00, 0xFF, 0x62, 0xD7, 0x0A])
    ]


async def test_set_hue_duration(lamp, client):
    await lamp.set_hue(hue=0, saturation=0, brightness=100, duration_ms=1000)
    assert written_commands(client) == [
        bytes([0xA0, 0x01, 0x02, 0x01, 0x03, 0xE8, 0x00, 0x00, 0x00, 0xFF])
    ]


async def test_set_hue_invalid_does_not_connect(lamp):
    with pytest.raises(ValueError):
        await lamp.set_hue(hue=400, saturation=50, brightness=50)
    lamp.establish_mock.assert_not_awaited()


async def test_set_color_temperature(lamp, client):
    await lamp.set_color_temperature(3000)
    # 04 Modify Color Temperature: A0 01 04 KK KK
    assert written_commands(client) == [bytes([0xA0, 0x01, 0x04, 0x0B, 0xB8])]


async def test_set_color_temperature_out_of_range(lamp):
    with pytest.raises(ValueError):
        await lamp.set_color_temperature(5000)
    lamp.establish_mock.assert_not_awaited()


# --- current scene ----------------------------------------------------------


async def test_update_current_scene(lamp, client):
    client.read_gatt_char.return_value = b"\x05"
    await lamp.update_current_scene()
    client.read_gatt_char.assert_awaited_once_with(CURRENTSCENE_UUID)
    assert lamp.current_scene_id == 5
    assert lamp.is_on
    client.disconnect.assert_not_awaited()


async def test_update_current_scene_off(lamp, client):
    client.read_gatt_char.return_value = b"\x00"
    await lamp.update_current_scene()
    assert lamp.current_scene_id == 0
    assert not lamp.is_on


async def test_update_current_scene_disconnects_on_error(lamp, client):
    client.read_gatt_char.side_effect = OSError("gatt error")
    with pytest.raises(OSError):
        await lamp.update_current_scene()
    client.disconnect.assert_awaited_once()


def test_get_current_scene_compat(lamp):
    lamp._scenes = [Scene(id=5, name="Reading")]
    lamp._current_scene = 5
    assert lamp.get_current_scene(True) == 5
    assert lamp.get_current_scene() == "Reading"
    assert lamp.current_scene_name == "Reading"
    lamp._current_scene = 9
    assert lamp.current_scene_name is None
    with pytest.raises(ValueError):
        lamp.get_current_scene()


# --- scene enumeration --------------------------------------------------------


def install_scene_responses(client, responses: dict[int, bytes]) -> None:
    """Answer each Query Scene write with the canned indication for that id."""

    async def deliver(char_specifier, data, response):
        queried_id = data[3]
        callback = client.start_notify.call_args.kwargs["callback"]
        await callback(char_specifier, bytearray(responses[queried_id]))

    client.write_gatt_char.side_effect = deliver


async def test_update_scenes(lamp, client):
    # Query Scene response: 00 01 NN <utf-8 name>
    install_scene_responses(
        client,
        {
            0x00: bytes([0x00, 0x01, 0x03]) + "Off".encode(),
            0x03: bytes([0x00, 0x01, 0x07]) + "Lesen".encode(),
            0x07: bytes([0x00, 0x01, 0xFF]) + "Entspannen\x00".encode(),
        },
    )
    await lamp.update_scenes()
    assert lamp.scenes == [
        Scene(id=0, name="Off"),
        Scene(id=3, name="Lesen"),
        Scene(id=7, name="Entspannen"),  # trailing NUL stripped
    ]
    # queries walk the id chain: 0 -> 3 -> 7, then FF terminates
    assert written_commands(client) == [
        bytes([0xA0, 0x01, 0x01, 0x00]),
        bytes([0xA0, 0x01, 0x01, 0x03]),
        bytes([0xA0, 0x01, 0x01, 0x07]),
    ]
    # notifications are stopped but the connection is kept for reuse
    client.stop_notify.assert_awaited_once_with(CHARACTERISTIC_UUID)
    client.disconnect.assert_not_awaited()


async def test_update_scenes_twice_does_not_duplicate(lamp, client):
    install_scene_responses(
        client, {0x00: bytes([0x00, 0x01, 0xFF]) + "Off".encode()}
    )
    await lamp.update_scenes()
    await lamp.update_scenes()
    assert lamp.scenes == [Scene(id=0, name="Off")]


async def test_update_scenes_error_status_raises(lamp, client):
    # status FC = Forbidden (security code set)
    install_scene_responses(client, {0x00: bytes([0xFC, 0x01, 0x00])})
    with pytest.raises(RuntimeError, match="0xfc"):
        await lamp.update_scenes()
    assert lamp.scenes == []
    client.stop_notify.assert_awaited_once_with(CHARACTERISTIC_UUID)


# --- update() ----------------------------------------------------------------


async def test_update_refreshes_scenes_once(lamp, client):
    install_scene_responses(
        client, {0x00: bytes([0x00, 0x01, 0xFF]) + "Off".encode()}
    )
    client.read_gatt_char.return_value = b"\x00"
    await lamp.update()
    assert lamp.scenes == [Scene(id=0, name="Off")]
    client.start_notify.assert_awaited_once()
    await lamp.update()
    # scene list is not re-read on subsequent updates
    client.start_notify.assert_awaited_once()


# --- discovery ----------------------------------------------------------------


async def test_find_lamp_returns_none_when_not_found():
    with patch(
        "pylukeroberts.pylukeroberts.BleakScanner.find_device_by_filter",
        new=AsyncMock(return_value=None),
    ) as finder:
        assert await find_lamp(timeout=5.0) is None
    assert finder.call_args.kwargs["timeout"] == 5.0


async def test_idle_disconnect_swallows_transport_errors(lamp, client):
    await lamp.set_brightness(10)
    client.disconnect.side_effect = OSError("dbus went away")
    # must not raise and must not leave an unretrieved task exception
    await lamp._idle_disconnect()
    client.disconnect.assert_awaited_once()


async def test_set_downlight(lamp, client):
    await lamp.set_downlight(kelvin=3000, brightness=50)
    # 02 Immediate Light, downlight packet: A0 01 02 02 DD DD KK KK BB
    # kelvin 3000 = 0x0BB8, brightness 50% -> 127 = 0x7F, duration 0
    assert written_commands(client) == [
        bytes([0xA0, 0x01, 0x02, 0x02, 0x00, 0x00, 0x0B, 0xB8, 0x7F])
    ]


async def test_set_downlight_duration(lamp, client):
    await lamp.set_downlight(kelvin=2700, brightness=100, duration_ms=1000)
    assert written_commands(client) == [
        bytes([0xA0, 0x01, 0x02, 0x02, 0x03, 0xE8, 0x0A, 0x8C, 0xFF])
    ]


async def test_set_downlight_invalid_does_not_connect(lamp):
    with pytest.raises(ValueError):
        await lamp.set_downlight(kelvin=5000, brightness=50)
    with pytest.raises(ValueError):
        await lamp.set_downlight(kelvin=3000, brightness=101)
    with pytest.raises(ValueError):
        await lamp.set_downlight(kelvin=3000, brightness=50, duration_ms=70000)
    lamp.establish_mock.assert_not_awaited()
