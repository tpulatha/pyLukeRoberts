# pyLukeRoberts

This library enables control of Luke Roberts Luvo lamps via Bluetooth Low Energy. It was written as a library to power a future Home Assistant Plug-In.



## Table of Contents

- [Capabilities](#capabilities)
- [Installation](#installation)
- [Usage](#usage)
- [Contributing](#contributing)
- [License](#license)
- [Contact](#contact)

## Capabilities
* Discover Luke Roberts Luvo lamps
* Switch Lamps On/Off
* Read all configured scenes
* Read current scene
* Change scene
* Change Color for Uplight

Future Features
* Change Brightness
* Change Color Temperature for Downlight and Uplight


## Installation


```bash
# Install via pypi
pip install pylukeroberts
```

## Dependencies

pyLukeRoberts uses bleak for Bluetooth Low Energy connectivity

## Usage

Example from `examples/set_scene.py`

```python
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
```

## Contributing

Guidelines for contributing to the project.

1. Fork the repository.
2. Create a new branch (`git checkout -b feature-branch`).
3. Make your changes.
4. Commit your changes (`git commit -m 'Add some feature'`).
5. Push to the branch (`git push origin feature-branch`).
6. Open a pull request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contact

Timur Pulathaneli - [timur@koeln.de](mailto:timur@koeln.de)

Project Link: [https://github.com/tpulatha/pylukeroberts](https://github.com/tpulatha/pylukeroberts)
