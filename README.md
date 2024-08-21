# WheelRepairer

WheelRepairer is a Python tool designed to modify wheel files by removing specific libraries, updating RPATH, and replacing library names. It's particularly useful for customizing wheels built with Maturin or other tools, allowing for fine-grained control over the contents and dependencies of wheel files.

## Features

- Remove specific files from wheel based on glob patterns and regular expressions
- Set RPATH for .so files
- Replace library names using glob patterns or regular expressions
- Apply different configurations for different .so files using wildcard patterns
- Support for dry-run mode to preview changes without modifying files
- Preserve wheel integrity while modifying its contents
- Display dynamic state of .so files after patching, including RPATH, NEEDED libraries, and detailed dynamic section information

## Installation

Clone this repository and install the required dependencies:

```bash
git clone https://github.com/yourusername/wheel-repairer.git
cd wheel-repairer
pip install -r requirements.txt
apt-get install readelf -y
```

## Usage

Basic usage:

```bash
python wheel_repairer.py /path/to/your/wheel.whl \
    --exclude "libtorch_cpu-*.so" \
    --exclude "libgomp-*.so.1" \
    --exclude-regex "^furiosa\.libs/libc10.*\.so$" \
    --config config.json \
    --dry-run
```

### Arguments

- `wheel_path`: Path to the wheel file to repair (required)
- `-o, --output-dir`: Output directory for repaired wheels (default: "repaired_wheels")
- `--exclude`: Glob patterns of files to exclude (can be used multiple times)
- `--exclude-regex`: Regex patterns of files to exclude (can be used multiple times)
- `--config`: Path to JSON configuration file for .so specific settings
- `--dry-run`: Perform a dry run without making changes

## Configuration File

The configuration file (e.g., `config.json`) supports wildcard patterns for .so files:

```json
{
  "native_runtime.*.so": {
    "rpath": "$ORIGIN/../furiosa.libs:$ORIGIN:$ORIGIN/../",
    "replace": [
      ["libtorch_cpu*.so", "libtorch_cpu.so"],
      ["r\"^(?:.*/)?(([^/]+)-[0-9a-f]{8}(\\.so(?:\\.[0-9]+)*))$\"", "(\\2\\3)"]
    ]
  }
}
```

This structure allows you to specify different RPATH and replacement rules for groups of .so files that match a certain pattern.

- The key (e.g., "native_runtime.*.so") is a wildcard pattern that matches .so file names.
- `rpath`: Specifies the new RPATH to set for matching .so files.
- `replace`: A list of [pattern, replacement] pairs for library name replacements.
  - If the pattern starts with `r"` and ends with `"`, it's treated as a regular expression.
  - Otherwise, it's treated as a glob pattern.

## Workflow

WheelRepairer operates in three main steps:

1. **Initialization and File Inspection**
   - Parse command line arguments and configuration file
   - Initialize WheelRepairer with wheel_path, output_dir, exclude patterns, exclude regex, and .so configurations
   - Inspect wheel contents
   - Identify files to exclude based on glob patterns and regex
   - *Inputs used: wheel_path, output_dir, --exclude, --exclude-regex, --config, --dry-run*

2. **Wheel Modification**
   - Extract wheel contents to temporary directory
   - Remove excluded files (or simulate removal in dry-run mode)
   - For each .so file:
     - Find matching configuration using wildcard patterns
     - Apply specific configurations (RPATH and replacements) if available (or simulate in dry-run mode)
     - Display dynamic state of the .so file after patching, including RPATH, NEEDED libraries, and detailed dynamic section information
   - *Inputs used: configurations from config file, --dry-run*

3. **Wheel Reconstruction and Finalization**
   - Create new wheel file with modified contents (skipped in dry-run mode)
   - Save new wheel file to output directory (skipped in dry-run mode)
   - Clean up temporary files
   - *Inputs used: output_dir, --dry-run*

This workflow ensures that the wheel file is systematically modified according to the specified parameters, maintaining its integrity while applying the desired changes. The dry-run option allows users to preview the changes without actually modifying the wheel file.

## Requirements

- Python 3.6+
- patchelf (must be installed on the system)
- readelf (part of binutils, must be installed on the system)


## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Troubleshooting

If you encounter any issues or errors, please check the following:

1. Ensure that patchelf is installed and accessible in your system PATH.
2. Verify that the wheel file you're trying to modify is accessible and not corrupted.
3. Check your configuration file for any syntax errors.

If problems persist, please open an issue on the GitHub repository with a detailed description of the problem, including any error messages and your command-line arguments.

## Acknowledgments

- This tool uses `patchelf` for modifying ELF files.
- Inspired by the need to customize Python wheels for specific environments and dependencies.