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

You can install WheelRepairer either directly using pip or by cloning the repository.

### Method 1: Direct installation using pip

You can install WheelRepairer directly from the GitHub repository using pip:

```bash
pip install git+https://github.com/furiosa-ai/wheel_repairer.git
```

### Method 2: Cloning the repository

1. Clone this repository:
   ```bash
   git clone https://github.com/furiosa-ai/wheel_repairer.git
   cd wheel-repairer
   ```

2. Install the required Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### System Dependencies

Regardless of the installation method, you need to install the following system dependencies:

- patchelf:
  - On Ubuntu/Debian: `sudo apt-get install patchelf`
  - On CentOS/RHEL: `sudo yum install patchelf`
- readelf (part of binutils):
  - On Ubuntu/Debian: `sudo apt-get install binutils`
  - On CentOS/RHEL: `sudo yum install binutils`

After installation, you can verify the installation by running:

```bash
wheel_repairer --version
```

This should display the version of WheelRepairer if it's correctly installed.

## Usage

Basic usage:

```bash
python wheel_repairer.py /path/to/your/wheel.whl --config config.json --dry-run
```

### Arguments

- `wheel_path`: Path to the wheel file to repair (required)
- `-o, --output-dir`: Output directory for repaired wheels (default: "repaired_wheels")
- `--config`: Path to JSON configuration file (required)
- `--dry-run`: Perform a dry run without making changes

## Configuration File

WheelRepairer supports both YAML and JSON configuration files. YAML is recommended for its better readability.

### YAML Configuration (config.yaml)

```yaml
exclude:
  - "libtorch_cpu-*.so"
  - "libgomp-*.so.1"
  - "libc10-*.so"
exclude_regex:
  - "^furiosa\\.libs/libc10.*\\.so$"
so_configs:
  "native_runtime.*.so":
    rpath: "$ORIGIN:$ORIGIN/../"
    replace:
      - ["libtorch_cpu*.so", "libtorch_cpu.so"]
      - ['r"^(?:.*/)?(([^/]+)-[0-9a-f]{8}(\.so(?:\.[0-9]+)*))$"', '\2\3']
```

### JSON Configuration (config.json)

```json
{
  "exclude": [
    "libtorch_cpu-*.so",
    "libgomp-*.so.1",
    "libc10-*.so"
  ],
  "exclude_regex": [
    "^furiosa\\.libs/libc10.*\\.so$"
  ],
  "so_configs": {
    "native_runtime.*.so": {
      "rpath": "$ORIGIN/../furiosa.libs:$ORIGIN:$ORIGIN/../",
      "replace": [
        ["libtorch_cpu*.so", "libtorch_cpu.so"],
        ["r\"^(?:.*/)?(([^/]+)-[0-9a-f]{8}(\\.so(?:\\.[0-9]+)*))$\"", "(\\2\\3)"]
      ]
    }
  }
}
```

Configuration file structure:

- `exclude`: List of glob patterns for files to exclude
- `exclude_regex`: List of regex patterns for files to exclude
- `so_configs`: Configurations for .so files
  - Keys are wildcard patterns that match .so file names
  - `rpath`: Specifies the new RPATH to set for matching .so files
  - `replace`: A list of [pattern, replacement] pairs for library name replacements
    - If the pattern starts with `r"` and ends with `"`, it's treated as a regular expression
    - Otherwise, it's treated as a glob pattern

## Workflow

WheelRepairer operates in three main steps:

1. **Initialization and File Inspection**
   - Parse command line arguments and configuration file
   - Initialize WheelRepairer with wheel_path, output_dir, and configurations
   - Inspect wheel contents
   - Identify files to exclude based on glob patterns and regex from the config
   - *Inputs used:*
     - Config file: 'exclude', 'exclude_regex'

2. **Wheel Modification**
   - Extract wheel contents to temporary directory
   - Remove excluded files (or simulate removal in dry-run mode)
   - For each .so file:
     - Find matching configuration using wildcard patterns
     - Apply specific configurations (RPATH and replacements) if available (or simulate in dry-run mode)
     - Display dynamic state of the .so file after patching, including RPATH, NEEDED libraries, and detailed dynamic section information
   - Update RECORD file to reflect changes
   - *Inputs used:*
     - Config file: 'so_configs' (including 'rpath' and 'replace' sub-fields)

3. **Wheel Reconstruction and Finalization**
   - Create new wheel file with modified contents (skipped in dry-run mode)
   - Save new wheel file to output directory (skipped in dry-run mode)
   - Clean up temporary files

This workflow ensures that the wheel file is systematically modified according to the specified parameters, maintaining its integrity while applying the desired changes. The dry-run option allows users to preview the changes without actually modifying the wheel file.

Config File Fields Used:
- 'exclude': List of glob patterns for files to exclude (used in step 1)
- 'exclude_regex': List of regex patterns for files to exclude (used in step 1)
- 'so_configs': Configurations for .so files (used in step 2)
  - Keys are wildcard patterns that match .so file names
  - 'rpath': Specifies the new RPATH to set for matching .so files
  - 'replace': A list of [pattern, replacement] pairs for library name replacements

## Requirements

- Python 3.6+
- patchelf
- readelf (part of binutils)
- PyYAML

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Troubleshooting

If you encounter any issues or errors, please check the following:

1. Ensure that patchelf and readelf are installed and accessible in your system PATH.
2. Verify that the wheel file you're trying to modify is accessible and not corrupted.
3. Check your configuration file for any syntax errors.

If problems persist, please open an issue on the GitHub repository with a detailed description of the problem, including any error messages and your command-line arguments.

## Acknowledgments

- This tool uses `patchelf` for modifying ELF files and `readelf` for displaying dynamic information.
- Inspired by the need to customize Python wheels for specific environments and dependencies.