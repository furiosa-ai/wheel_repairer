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
    def __init__(self, wheel_path, output_dir="repaired_wheels", config=None):
        self.wheel_path = wheel_path
        self.output_dir = output_dir
        self.config = config or {}
        self.exclude_patterns = self.config.get('exclude', [])
        self.exclude_regex = self.config.get('exclude_regex', [])
        self.so_configs = self.config.get('so_configs', {})
        self.wheel_files = self._inspect_wheel()
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
                                print(f"Replaced {lib} with {new_lib}")
                    else:
                        libs = fnmatch.filter(subprocess.check_output(['patchelf', '--print-needed', so_file], universal_newlines=True).splitlines(), pattern)
                        for lib in libs:
                            subprocess.run(['patchelf', '--replace-needed', lib, replacement, so_file], check=True)
                            print(f"Replaced {lib} with {replacement}")

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
                
    def find_repaired_wheel(self):
        """Find the repaired wheel in the output directory based on the original wheel name."""
        original_name = os.path.basename(self.wheel_path)
        name_parts = original_name.split('-')
        
        # Create a pattern that matches the package name and version, but allows for changes in the platform tag
        name_pattern = f"{'-'.join(name_parts[:2])}-*-{'-'.join(name_parts[3:-1])}-*.whl"
        
        repaired_wheels = glob.glob(os.path.join(self.output_dir, name_pattern))
        if repaired_wheels:
            return max(repaired_wheels, key=os.path.getctime)  # Return the most recently created wheel
        return None
    
    def remove_dependencies(self, wheel_dir, files_to_exclude):
        """Remove dependencies and references to excluded libraries."""
        print("\nRemoving dependencies and references to excluded libraries...")
        so_file = os.path.join(wheel_dir, 'furiosa/native_runtime.cpython-310-x86_64-linux-gnu.so')
        
        if os.path.exists(so_file):
            # 현재 의존성 출력
            print("Current dependencies:")
            subprocess.run(['ldd', so_file])

            for file in files_to_exclude:
                lib_name = os.path.basename(file)
                subprocess.run(['patchelf', '--remove-needed', lib_name, so_file])
                print(f"Removed dependency: {lib_name}")
                
            print("\nDependencies after removal:")
            subprocess.run(['ldd', so_file])
        else:
            print(f"Warning: {so_file} not found. Skipping dependency removal.")

    def remove_excluded_files(self, wheel_path, files_to_exclude):
        """Remove specified files from the wheel and apply patches."""
        print(f"\nStarting process to remove excluded files and apply patches: {wheel_path}")
        with tempfile.TemporaryDirectory() as tmpdir:
            print(f"Created temporary directory: {tmpdir}")
            
            # Unzip the wheel
            print("Unzipping the wheel file...")
            with zipfile.ZipFile(wheel_path, 'r') as zip_ref:
                zip_ref.extractall(tmpdir)
            print("Wheel file unzipped successfully.")
            
            # Remove excluded files
            print("\nRemoving excluded files...")
            for file in files_to_exclude:
                file_path = os.path.join(tmpdir, file)
                if os.path.exists(file_path):
                    os.remove(file_path)
                    print(f"  Removed: {file}")
                else:
                    print(f"  File not found (already removed or never existed): {file}")
            
            # Apply patches to .so files
            for root, _, files in os.walk(tmpdir):
                for file in files:
                    if file.endswith('.so'):
                        self.apply_patches(os.path.join(root, file))
            
            # Create a new wheel without excluded files and with patched .so files
            print("\nCreating new wheel...")
            new_wheel_path = wheel_path.replace('.whl', '_repaired.whl')
            with zipfile.ZipFile(new_wheel_path, 'w', zipfile.ZIP_DEFLATED) as new_zip:
                for root, _, files in os.walk(tmpdir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arc_name = os.path.relpath(file_path, tmpdir)
                        new_zip.write(file_path, arc_name)
                        print(f"  Added to new wheel: {arc_name}")
            
            # Replace the original wheel with the new one
            print(f"\nReplacing original wheel with repaired version...")
            shutil.move(new_wheel_path, wheel_path)
            print(f"Wheel file updated: {wheel_path}")
        """Remove specified files from the wheel and their dependencies."""
        print(f"\nStarting process to remove excluded files from: {wheel_path}")
        with tempfile.TemporaryDirectory() as tmpdir:
            print(f"Created temporary directory: {tmpdir}")
            
            # Unzip the wheel
            print("Unzipping the wheel file...")
            with zipfile.ZipFile(wheel_path, 'r') as zip_ref:
                zip_ref.extractall(tmpdir)
            print("Wheel file unzipped successfully.")
            
            # Remove excluded files
            print("\nRemoving excluded files...")
            for file in files_to_exclude:
                file_path = os.path.join(tmpdir, file)
                if os.path.exists(file_path):
                    os.remove(file_path)
                    print(f"  Removed: {file}")
                else:
                    print(f"  File not found (already removed or never existed): {file}")
            
            # Remove dependencies
            self.remove_dependencies(tmpdir, files_to_exclude)
            
            # Create a new wheel without excluded files
            print("\nCreating new wheel without excluded files...")
            new_wheel_path = wheel_path.replace('.whl', '_cleaned.whl')
            with zipfile.ZipFile(new_wheel_path, 'w', zipfile.ZIP_DEFLATED) as new_zip:
                for root, _, files in os.walk(tmpdir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arc_name = os.path.relpath(file_path, tmpdir)
                        new_zip.write(file_path, arc_name)
                        print(f"  Added to new wheel: {arc_name}")
            
            # Replace the original wheel with the new one
            print(f"\nReplacing original wheel with cleaned version...")
            shutil.move(new_wheel_path, wheel_path)
            print(f"Wheel file updated: {wheel_path}")
            
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
    parser.add_argument("--config", required=True, help="Path to JSON configuration file")
    parser.add_argument("--dry-run", action="store_true", help="Perform a dry run without making changes")
    args = parser.parse_args()

    with open(args.config, 'r') as f:
        config = json.load(f)

    repairer = WheelRepairer(args.wheel_path, args.output_dir, config)
    repairer.repair(dry_run=args.dry_run)
    
if __name__ == "__main__":
    main()