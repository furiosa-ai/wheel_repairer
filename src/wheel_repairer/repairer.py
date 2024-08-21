import subprocess
import glob
import os
import zipfile
import shutil
import tempfile
import re
import argparse
import fnmatch
import json
import yaml
import hashlib
import base64

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
        config (dict): Configuration dictionary containing repair settings.
        exclude_patterns (list): Glob patterns of files to be excluded from the wheel.
        exclude_regex (list): Regex patterns of files to be excluded from the wheel.
        so_configs (dict): Configurations for .so files.
        wheel_files (list): List of files inside the wheel.
        exclude_files (list): Files matching the exclude patterns or regex.

    Note:
        The presence of two platform tags (e.g., manylinux_2_17 and manylinux2014) 
        indicates compatibility with both newer and older manylinux standards, 
        maximizing the wheel's compatibility across different systems.

    This class supports both glob-style patterns and regular expressions for excluding files.
    Glob patterns are simpler and suitable for basic file matching, while regular expressions
    offer more powerful and flexible pattern matching capabilities.
    """

    def __init__(self, wheel_path, output_dir="repaired_wheels", config=None):
        """Initialize the WheelRepairer.

        Args:
            wheel_path (str): Path to the wheel file to be repaired.
            output_dir (str, optional): Directory where the repaired wheel will be saved.
                Defaults to "repaired_wheels".
            config (dict, optional): Configuration dictionary containing repair settings.
                Defaults to None.
        """
        self.wheel_path = wheel_path
        self.output_dir = output_dir
        self.config = config or {}
        self.exclude_patterns = self.config.get('exclude', [])
        self.exclude_regex = self.config.get('exclude_regex', [])
        self.so_configs = self.config.get('so_configs', {})
        self.wheel_files = self._inspect_wheel()
        self.exclude_files = self._find_matching_files()

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

    def print_wheel_info(self):
        """Print information about the wheel and files to be excluded."""
        print(f"Detected platform: {self.platform}")
        print("\nFiles in the wheel:")
        for file in self.wheel_files:
            print(f"  {file}")
        print("\nFiles to be excluded:")
        for file in self.exclude_files:
            print(f"  {file}")
            
    def get_so_config(self, so_file):
        so_name = os.path.basename(so_file)
        for pattern, config in self.so_configs.items():
            if fnmatch.fnmatch(so_name, pattern):
                return config
        return None
    
    def apply_patches(self, so_file):
        print(f"\nApplying patches to: {so_file}")
        config = self.get_so_config(so_file)

        if config:
            if 'rpath' in config:
                subprocess.run(['patchelf', '--set-rpath', config['rpath'], so_file], check=True)
                print(f"Set RPATH to: {config['rpath']}")

            if 'replace' in config:
                for pattern, replacement in config['replace']:
                    if pattern.startswith('r"') and pattern.endswith('"'):
                        regex = re.compile(pattern[2:-1])
                        output = subprocess.check_output(['patchelf', '--print-needed', so_file], universal_newlines=True)
                        for lib in output.splitlines():
                            if regex.match(lib):
                                new_lib = regex.sub(replacement, lib)
                                subprocess.run(['patchelf', '--replace-needed', lib, new_lib, so_file], check=True)
                                print(f"Replaced {lib} with {new_lib} by {pattern}=>{replacement}")
                    else:
                        libs = fnmatch.filter(subprocess.check_output(['patchelf', '--print-needed', so_file], universal_newlines=True).splitlines(), pattern)
                        for lib in libs:
                            subprocess.run(['patchelf', '--replace-needed', lib, replacement, so_file], check=True)
                            print(f"Replaced {lib} with {replacement} by {pattern}")

            print("Patches applied successfully.")
            self.display_dynamic_state(so_file)
        else:
            print("No specific configuration found for this .so file. Skipping patches.")

    def display_dynamic_state(self, so_file):
        print(f"\nDynamic state of {so_file} after patching:")
        
        # Display RPATH
        rpath = subprocess.check_output(['patchelf', '--print-rpath', so_file], universal_newlines=True).strip()
        print(f"RPATH: {rpath}")
        
        # Display NEEDED libraries
        needed = subprocess.check_output(['patchelf', '--print-needed', so_file], universal_newlines=True).strip().split('\n')
        print("NEEDED libraries:")
        for lib in needed:
            print(f"  {lib}")
        
        # Display more detailed information using readelf
        print("\nDetailed dynamic section information:")
        readelf_output = subprocess.check_output(['readelf', '-d', so_file], universal_newlines=True)
        print(readelf_output)
                
    def find_dist_info_dir(self, tmpdir):
        for item in os.listdir(tmpdir):
            if item.endswith('.dist-info'):
                return item
        raise ValueError("Could not find .dist-info directory in the wheel")

    def check_package_name_and_version(self, dist_info_dir):
        match = re.match(r'(.+)-(.+)\.dist-info', dist_info_dir)
        if match is None:
            raise ValueError(f"Could not extract package name and version from {dist_info_dir}")
        return match.group(1), match.group(2)

    def update_record_file(self, tmpdir):
        dist_info_dir = self.find_dist_info_dir(tmpdir)
        _, _ = self.check_package_name_and_version(dist_info_dir)
        record_file = os.path.join(tmpdir, dist_info_dir, 'RECORD')

        new_record_entries = []

        for root, _, files in os.walk(tmpdir):
            for file in files:
                file_path = os.path.join(root, file)
                rel_path = os.path.relpath(file_path, tmpdir)
                
                if rel_path == os.path.join(dist_info_dir, 'RECORD'):
                    new_record_entries.append(f"{rel_path},,\n")
                else:
                    with open(file_path, 'rb') as f:
                        file_hash = hashlib.sha256(f.read()).digest()
                        hash_value = base64.urlsafe_b64encode(file_hash).rstrip(b'=').decode()
                    file_size = os.path.getsize(file_path)
                    new_record_entries.append(f"{rel_path},sha256={hash_value},{file_size}\n")

        with open(record_file, 'w') as f:
            f.writelines(new_record_entries)
                        
    def repair(self, dry_run=False):
        print(f"\nRepairing wheel: {self.wheel_path}")
        os.makedirs(self.output_dir, exist_ok=True)
        output_wheel = os.path.join(self.output_dir, os.path.basename(self.wheel_path))

        if dry_run:
            print("Dry run mode: No changes will be made.")

        with tempfile.TemporaryDirectory() as tmpdir:
            print(f"Created temporary directory: {tmpdir}")
            
            with zipfile.ZipFile(self.wheel_path, 'r') as zip_ref:
                zip_ref.extractall(tmpdir)
            
            for root, _, files in os.walk(tmpdir):
                for file in files:
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, tmpdir)
                    
                    if rel_path in self.exclude_files:
                        if not dry_run:
                            os.remove(file_path)
                        print(f"{'Would remove' if dry_run else 'Removed'}: {rel_path}")
                    elif file.endswith('.so'):
                        if not dry_run:
                            self.apply_patches(file_path)
                        else:
                            print(f"Would apply patches to: {rel_path}")
            
            if not dry_run:
                self.update_record_file(tmpdir)
                with zipfile.ZipFile(output_wheel, 'w', zipfile.ZIP_DEFLATED) as new_zip:
                    for root, _, files in os.walk(tmpdir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arc_name = os.path.relpath(file_path, tmpdir)
                            new_zip.write(file_path, arc_name)
                            print(f"Added to new wheel: {arc_name}")
                print(f"\nRepaired wheel saved as: {output_wheel}")
            else:
                print("\nDry run completed. No changes were made.")

def main():
    parser = argparse.ArgumentParser(description="Repair wheel files by removing and replacing libraries.")
    parser.add_argument("wheel_path", help="Path to the wheel file to repair")
    parser.add_argument("-o", "--output-dir", default="repaired_wheels", help="Output directory for repaired wheels")
    parser.add_argument("--config", required=True, help="Path to YAML or JSON configuration file")
    parser.add_argument("--dry-run", action="store_true", help="Perform a dry run without making changes")
    args = parser.parse_args()

    config = {}
    with open(args.config, 'r') as f:
        if args.config.endswith('.yaml') or args.config.endswith('.yml'):
            config = yaml.safe_load(f)
        else:
            config = json.load(f)

    repairer = WheelRepairer(args.wheel_path, args.output_dir, config)
    repairer.repair(dry_run=args.dry_run)
    
if __name__ == "__main__":
    main()