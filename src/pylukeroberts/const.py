"""Constants for the Luke Roberts BLE control API (docs/LR BT API v1.6.pdf)."""

SERVICE_UUID = "44092840-0567-11e6-b862-0002a5d5c51b"
CHARACTERISTIC_UUID = "44092842-0567-11e6-b862-0002a5d5c51b"

CURRENTSCENE_UUID = "44092844-0567-11e6-b862-0002a5d5c51b"

UNKNOWNONE_UUID = "44092847-0567-11e6-b862-0002a5d5c51b"
UNKNOWNTWO_UUID = "44092848-0567-11e6-b862-0002a5d5c51b"

# External API command framing: A0 <version> <opcode> <parameters...>
COMMAND_PREFIX = 0xA0
API_V1 = 0x01
API_V2 = 0x02

# Opcodes and the API version byte the spec assigns them to
OPCODE_PING = 0x00                       # V1 and V2
OPCODE_QUERY_SCENE = 0x01                # V1
OPCODE_IMMEDIATE_LIGHT = 0x02            # V1
OPCODE_BRIGHTNESS = 0x03                 # V1
OPCODE_COLOR_TEMPERATURE = 0x04          # V1
OPCODE_SELECT_SCENE = 0x05               # V2
OPCODE_NEXT_SCENE_BY_BRIGHTNESS = 0x06   # V2
OPCODE_ADJUST_COLOR_TEMPERATURE = 0x07   # V2
OPCODE_RELATIVE_BRIGHTNESS = 0x08        # V2

# Immediate Light content flags
IMMEDIATE_LIGHT_UPLIGHT = 0x01
IMMEDIATE_LIGHT_DOWNLIGHT = 0x02

# Scene ids
SCENE_OFF = 0x00      # scene 0 is the Off scene
SCENE_DEFAULT = 0xFF  # selects the power-on default scene
SCENE_LIST_END = 0xFF # "next scene id" terminator in Query Scene responses

# Response status codes (byte 0 of an indication)
STATUS_OK = 0x00

# Downlight color temperature limits in Kelvin
MIN_KELVIN = 2700
MAX_KELVIN = 4000
