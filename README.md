# Wheel Repairer

Wheel Repairer is a Python tool designed to repair wheel files using auditwheel. It provides an easy-to-use interface for excluding specific files from wheels and repairing them to meet the manylinux standard.

## Features

- Automatically detects the platform tag from wheel filenames
- Allows exclusion of specific files from wheels
- Supports dry run mode for testing without making changes
- Command-line interface for easy integration into build processes

## Installation

You can install Wheel Repairer using pip:

```
pip install wheel_repairer
```

## Usage

### As a Command-Line Tool

You can use Wheel Repairer directly from the command line:

```
wheel_repairer /path/to/your/wheel.whl
```

Options:
- `-o`, `--output-dir`: Specify the output directory for repaired wheels (default: "repaired_wheels")
- `--dry-run`: Perform a dry run without making changes

Example:
```
wheel_repairer /path/to/your/wheel.whl --output-dir repaired --dry-run
```

### As a Python Module

You can also use Wheel Repairer in your Python scripts:

```python
from wheel_repairer import WheelRepairer

repairer = WheelRepairer("/path/to/your/wheel.whl")
repairer.repair(dry_run=True)
```

## Requirements

- Python 3.6+
- auditwheel

## Contributing

Contributions to Wheel Repairer are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- This tool uses `auditwheel` for wheel repair functionality.

## Support

If you encounter any problems or have any questions, please open an issue on the [GitHub repository](https://github.com/yourusername/wheel_repairer).