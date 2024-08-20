# Wheel Repairer

Wheel Repairer is a Python tool designed to repair wheel files using auditwheel. It provides an easy-to-use interface for excluding specific files from wheels based on glob patterns or regular expressions and repairing them to meet the manylinux standard.

## Features

- Automatically detects the platform tag from wheel filenames
- Allows exclusion of files based on glob patterns
- Supports regular expression patterns for more flexible file exclusion
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
- `--exclude`: Specify glob patterns of files to exclude (can be used multiple times)
- `--exclude-regex`: Specify regex patterns of files to exclude (can be used multiple times)
- `--dry-run`: Perform a dry run without making changes
- `--debug`: Enable debug output for detailed information on pattern matching

Example:
```
wheel_repairer /path/to/your/wheel.whl \
    --output-dir repaired \
    --exclude "*.so" \
    --exclude-regex "lib.*\.so\.1" \
    --dry-run \
    --debug
```

### As a Python Module

You can also use Wheel Repairer in your Python scripts:

```python
from wheel_repairer import WheelRepairer

repairer = WheelRepairer(
    "/path/to/your/wheel.whl",
    exclude_patterns=["*.so"],
    exclude_regex=["lib.*\.so\.1"]
)
repairer.repair(dry_run=True)
```

## File Exclusion Patterns

Wheel Repairer supports two types of file exclusion patterns:

1. Glob Patterns (--exclude):
   - Simple wildcard patterns
   - Example: `*.so`, `lib*.so`

2. Regular Expressions (--exclude-regex):
   - More powerful and flexible pattern matching
   - Example: `lib.*\.so\.1`, `^furiosa\.libs/.*`

Choose the appropriate pattern type based on your needs. Glob patterns are simpler and suitable for basic file matching, while regular expressions offer more advanced pattern matching capabilities.

## Requirements

- Python 3.6+
- auditwheel

## Contributing

Contributions to Wheel Repairer are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License

## Acknowledgments

- This tool uses `auditwheel` for wheel repair functionality.

## Support

If you encounter any problems or have any questions, please open an issue.