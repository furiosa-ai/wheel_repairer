import subprocess
import glob
import os
import zipfile
import re
import argparse

class WheelRepairer:
    """A class to repair wheel files using auditwheel.

    This class handles wheel files named according to the following convention:
    {distribution}-{version}(-{build tag})?-{python tag}-{abi tag}-{platform tag}.whl

    Example:
        furiosa_native_runtime-0.11.0.dev240805-cp310-cp310-manylinux_2_17_x86_64.manylinux2014_x86_64.whl

    Where:
    - furiosa_native_runtime: Distribution name
    - 0.11.0.dev240805: Version number (development version)
    - cp310 (1st occurrence): Python tag (CPython 3.10)
    - cp310 (2nd occurrence): ABI tag (CPython 3.10 ABI)
    - manylinux_2_17_x86_64: First platform tag (newer manylinux naming convention)
    - manylinux2014_x86_64: Second platform tag (older manylinux naming convention)

    Attributes:
        wheel_path (str): Path to the wheel file to be repaired.
        output_dir (str): Directory where the repaired wheel will be saved.
        platform (str): Detected platform from the wheel filename.
        wheel_files (list): List of files inside the wheel.
        exclude_patterns (list): Glob patterns of files to be excluded from the wheel.
        exclude_regex (list): Regex patterns of files to be excluded from the wheel.
        exclude_files (list): Files matching the exclude patterns or regex.

    Note:
        The presence of two platform tags (e.g., manylinux_2_17 and manylinux2014) 
        indicates compatibility with both newer and older manylinux standards, 
        maximizing the wheel's compatibility across different systems.

    This class supports both glob-style patterns and regular expressions for excluding files.
    Glob patterns are simpler and suitable for basic file matching, while regular expressions
    offer more powerful and flexible pattern matching capabilities.
    """
    def __init__(self, wheel_path, output_dir="repaired_wheels", exclude_patterns=None, exclude_regex=None):
        """Initialize the WheelRepairer.

        Args:
            wheel_path (str): Path to the wheel file to be repaired.
            output_dir (str, optional): Directory where the repaired wheel will be saved. 
                Defaults to "repaired_wheels".
            exclude_patterns (list, optional): List of glob patterns for files to exclude. 
                Defaults to None.
            exclude_regex (list, optional): List of regex patterns for files to exclude. 
                Defaults to None.
        """
        self.wheel_path = wheel_path
        self.output_dir = output_dir
        self.platform = self._extract_platform()
        self.wheel_files = self._inspect_wheel()
        self.exclude_patterns = exclude_patterns or []
        self.exclude_regex = exclude_regex or []
        self.exclude_files = self._find_matching_files()

    def _extract_platform(self):
        """Extract the platform tag from the wheel filename.

        This method prioritizes the newer manylinux naming convention if present.

        Returns:
            str: The extracted platform tag, or a default value if not found.
        """
        match = re.search(r'(manylinux_\d+_\d+_[^.]+)', self.wheel_path)
        if match:
            return match.group(1)
        print("Could not detect platform from filename. Using default manylinux_2_24_x86_64.")
        return "manylinux_2_24_x86_64"

    def _inspect_wheel(self):
        """Inspect the contents of the wheel file.

        Returns:
            list: A list of file names contained in the wheel.
        """
        with zipfile.ZipFile(self.wheel_path, 'r') as zip_ref:
            return zip_ref.namelist()

    def _find_matching_files(self):
        """Find files in the wheel that match the exclude patterns or regex.

        Returns:
            list: A list of file names that match the exclude patterns or regex.
        """
        matching_files = set()
        print("\nDebugging information for pattern matching:")
        
        # Glob pattern matching
        for pattern in self.exclude_patterns:
            print(f"\nChecking glob pattern: {pattern}")
            if not pattern.startswith('*'):
                pattern = f'**/{pattern}'
            print(f"Adjusted glob pattern: {pattern}")
            for file in self.wheel_files:
                if glob.fnmatch.fnmatch(file, pattern):
                    print(f"  Matched (glob): {file}")
                    matching_files.add(file)
                else:
                    print(f"  Not matched (glob): {file}")
        
        # Regex pattern matching
        for regex in self.exclude_regex:
            print(f"\nChecking regex pattern: {regex}")
            pattern = re.compile(regex)
            for file in self.wheel_files:
                if pattern.search(file):
                    print(f"  Matched (regex): {file}")
                    matching_files.add(file)
                else:
                    print(f"  Not matched (regex): {file}")
        
        print("\nSummary of matched files:")
        for file in matching_files:
            print(f"  {file}")
        
        return list(matching_files)

    def prepare_command(self):
        """Prepare the auditwheel repair command.

        Returns:
            list: A list of command arguments for the auditwheel repair command.
        """
        cmd = [
            "auditwheel", "repair",
            "--plat", self.platform,
            "-w", self.output_dir
        ]
        for file in self.exclude_files:
            cmd.extend(["--exclude", os.path.basename(file)])
        cmd.append(self.wheel_path)
        return cmd

    def print_wheel_info(self):
        """Print information about the wheel and files to be excluded."""
        print(f"Detected platform: {self.platform}")
        print("\nFiles in the wheel:")
        for file in self.wheel_files:
            print(f"  {file}")
        print("\nFiles to be excluded:")
        for file in self.exclude_files:
            print(f"  {file}")

    def repair(self, dry_run=True):
        """Repair the wheel using auditwheel.

        Args:
            dry_run (bool, optional): If True, only print the command without executing it. 
                Defaults to True.
        """
        self.print_wheel_info()
        cmd = self.prepare_command()
        print("\nExecuting command:")
        print(" ".join(cmd))
        if not dry_run:
            subprocess.run(cmd)
            print(f"\nRepaired wheel should be in the '{self.output_dir}' directory.")
        else:
            print("\nDry run completed. No changes were made.")
        print("\nNote: Full paths are used for excluded files in the auditwheel command.")

def main():
    parser = argparse.ArgumentParser(description="Repair wheel files using auditwheel.")
    parser.add_argument("wheel_path", help="Path to the wheel file to repair")
    parser.add_argument("-o", "--output-dir", default="repaired_wheels", help="Output directory for repaired wheels")
    parser.add_argument("--exclude", action='append', default=[], help="Patterns of files to exclude (can be used multiple times)")
    parser.add_argument("--exclude-regex", action='append', default=[], help="Regex patterns of files to exclude (can be used multiple times)")
    parser.add_argument("--dry-run", action="store_true", help="Perform a dry run without making changes")
    args = parser.parse_args()

    repairer = WheelRepairer(args.wheel_path, args.output_dir, args.exclude, args.exclude_regex)
    repairer.repair(dry_run=args.dry_run)

if __name__ == "__main__":
    main()