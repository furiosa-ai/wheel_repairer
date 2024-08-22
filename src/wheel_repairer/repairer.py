import subprocess
import glob
import os
import zipfile
import tempfile
import re
import argparse
import fnmatch
import json
import yaml
import hashlib
import base64
import logging
from .mylogger import setup_logger, get_logger

class WheelRepairer:
    """
    A class to repair wheel files by removing and replacing libraries.

    This class handles the process of repairing wheel files, which includes
    inspecting the wheel contents, finding files to exclude, applying patches
    to shared objects, and creating a new repaired wheel file.

    Attributes:
        wheel_path (str): Path to the wheel file to be repaired.
        output_dir (str): Directory where the repaired wheel will be saved.
        config (dict): Configuration dictionary containing repair settings.
        exclude_patterns (list): Glob patterns of files to be excluded from the wheel.
        exclude_regex (list): Regex patterns of files to be excluded from the wheel.
        so_configs (dict): Configurations for .so files.
        wheel_files (list): List of files inside the wheel.
        exclude_files (list): Files matching the exclude patterns or regex.
        logger (logging.Logger): Logger instance for this class.
    """

    def __init__(self, wheel_path, output_dir="repaired_wheels", config=None):
        """
        Initialize the WheelRepairer instance.

        Args:
            wheel_path (str): Path to the wheel file to be repaired.
            output_dir (str, optional): Directory where the repaired wheel will be saved.
                Defaults to "repaired_wheels".
            config (dict, optional): Configuration dictionary containing repair settings.
                Defaults to None.
        """
        self.logger = get_logger()
        
        self.wheel_path = wheel_path
        self.output_dir = output_dir
        self.config = config or {}
        self.exclude_patterns = self.config.get('exclude', [])
        self.exclude_regex = self.config.get('exclude_regex', [])
        self.so_configs = self.config.get('so_configs', {})
        
        self.wheel_files = self._inspect_wheel()
        self.exclude_files = self._find_matching_files()

    def _inspect_wheel(self):
        """
        Inspect the contents of the wheel file.

        Returns:
            list: A list of file names contained in the wheel.
        """
        with zipfile.ZipFile(self.wheel_path, 'r') as zip_ref:
            return zip_ref.namelist()

    def _find_matching_files(self):
        """
        Find files in the wheel that match the exclude patterns or regex.

        This method logs detailed information about the matching process.

        Returns:
            list: A list of file names that match the exclude patterns or regex.
        """
        matching_files = set()
        self.logger.info("Debugging information for pattern matching:")
        
        # Glob pattern matching
        for pattern in self.exclude_patterns:
            self.logger.info(f"Checking glob pattern: {pattern}")
            if not pattern.startswith('*'):
                pattern = f'**/{pattern}'
            self.logger.info(f"Adjusted glob pattern: {pattern}")
            for file in self.wheel_files:
                if glob.fnmatch.fnmatch(file, pattern):
                    self.logger.info(f"  Matched (glob): {file}")
                    matching_files.add(file)
                else:
                    self.logger.debug(f"  Not matched (glob): {file}")
        
        # Regex pattern matching
        for regex in self.exclude_regex:
            self.logger.info(f"Checking regex pattern: {regex}")
            pattern = re.compile(regex)
            for file in self.wheel_files:
                if pattern.search(file):
                    self.logger.info(f"  Matched (regex): {file}")
                    matching_files.add(file)
                else:
                    self.logger.debug(f"  Not matched (regex): {file}")
        
        self.logger.info("Summary of matched files:")
        for file in matching_files:
            self.logger.info(f"  {file}")
        
        return list(matching_files)

    def print_wheel_info(self):
        """
        Print information about the wheel and files to be excluded.

        This method logs the list of all files in the wheel and the files that will be excluded.
        """
        self.logger.info(f"Files in the wheel:")
        for file in self.wheel_files:
            self.logger.info(f"  {file}")
        self.logger.info("Files to be excluded:")
        for file in self.exclude_files:
            self.logger.info(f"  {file}")
            
    def get_so_config(self, so_file):
        """
        Get the configuration for a specific .so file.

        Args:
            so_file (str): The name of the .so file.

        Returns:
            dict or None: The configuration for the .so file if found, None otherwise.
        """
        so_name = os.path.basename(so_file)
        for pattern, config in self.so_configs.items():
            if fnmatch.fnmatch(so_name, pattern):
                return config
        return None
    
    def apply_patches(self, so_file):
        """
        Apply patches to a shared object file.

        This method applies the configured patches to the specified .so file,
        which may include setting RPATH and replacing needed libraries.

        Args:
            so_file (str): Path to the .so file to be patched.
        """
        self.logger.info(f"Applying patches to: {so_file}")
        config = self.get_so_config(so_file)

        if config:
            if 'rpath' in config:
                subprocess.run(['patchelf', '--set-rpath', config['rpath'], so_file], check=True)
                self.logger.info(f"Set RPATH to: {config['rpath']}")

            if 'replace' in config:
                for pattern, replacement in config['replace']:
                    if pattern.startswith('r"') and pattern.endswith('"'):
                        regex = re.compile(pattern[2:-1])
                        output = subprocess.check_output(['patchelf', '--print-needed', so_file], universal_newlines=True)
                        for lib in output.splitlines():
                            if regex.match(lib):
                                new_lib = regex.sub(replacement, lib)
                                subprocess.run(['patchelf', '--replace-needed', lib, new_lib, so_file], check=True)
                                self.logger.info(f"Replaced {lib} with {new_lib} by {pattern}=>{replacement}")
                    else:
                        libs = fnmatch.filter(subprocess.check_output(['patchelf', '--print-needed', so_file], universal_newlines=True).splitlines(), pattern)
                        for lib in libs:
                            subprocess.run(['patchelf', '--replace-needed', lib, replacement, so_file], check=True)
                            self.logger.info(f"Replaced {lib} with {replacement} by {pattern}")

            self.logger.info("Patches applied successfully.")
            self.display_dynamic_state(so_file)
        else:
            self.logger.info("No specific configuration found for this .so file. Skipping patches.")

    def display_dynamic_state(self, so_file):
        """
        Display the dynamic state of a shared object file after patching.

        This method logs detailed information about the .so file's dynamic state,
        including RPATH, NEEDED libraries, and other dynamic section information.

        Args:
            so_file (str): Path to the .so file.
        """
        self.logger.info(f"Dynamic state of {so_file} after patching:")
        
        # Display RPATH
        rpath = subprocess.check_output(['patchelf', '--print-rpath', so_file], universal_newlines=True).strip()
        self.logger.info(f"RPATH: {rpath}")
        
        # Display NEEDED libraries
        needed = subprocess.check_output(['patchelf', '--print-needed', so_file], universal_newlines=True).strip().split('\n')
        self.logger.info("NEEDED libraries:")
        for lib in needed:
            self.logger.info(f"  {lib}")
        
        # Display more detailed information using readelf
        self.logger.info("Detailed dynamic section information:")
        readelf_output = subprocess.check_output(['readelf', '-d', so_file], universal_newlines=True)
        self.logger.info(readelf_output)
                
    def find_dist_info_dir(self, tmpdir):
        """
        Find the .dist-info directory in the extracted wheel.

        Args:
            tmpdir (str): Path to the directory containing the extracted wheel contents.

        Returns:
            str: Name of the .dist-info directory.

        Raises:
            ValueError: If the .dist-info directory is not found.
        """
        for item in os.listdir(tmpdir):
            if item.endswith('.dist-info'):
                return item
        raise ValueError("Could not find .dist-info directory in the wheel")

    def check_package_name_and_version(self, dist_info_dir):
        """
        Extract package name and version from the .dist-info directory name.

        Args:
            dist_info_dir (str): Name of the .dist-info directory.

        Returns:
            tuple: A tuple containing the package name and version.

        Raises:
            ValueError: If package name and version cannot be extracted.
        """
        match = re.match(r'(.+)-(.+)\.dist-info', dist_info_dir)
        if match is None:
            raise ValueError(f"Could not extract package name and version from {dist_info_dir}")
        return match.group(1), match.group(2)

    def update_record_file(self, tmpdir):
        """
        Update the RECORD file in the wheel with new file hashes and sizes.

        This method recalculates hashes and sizes for all files in the wheel
        and updates the RECORD file accordingly.

        Args:
            tmpdir (str): Path to the directory containing the extracted wheel contents.
        """
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
        """
        Repair the wheel file.

        This method performs the actual repair process on the wheel file.
        It extracts the wheel, applies the necessary patches and exclusions,
        and creates a new repaired wheel file.

        Args:
            dry_run (bool, optional): If True, simulate the repair process without
                making actual changes. Defaults to False.
        """
        self.logger.info(f"Repairing wheel: {self.wheel_path}")
        os.makedirs(self.output_dir, exist_ok=True)
        output_wheel = os.path.join(self.output_dir, os.path.basename(self.wheel_path))

        if dry_run:
            self.logger.info("Dry run mode: No changes will be made.")

        with tempfile.TemporaryDirectory() as tmpdir:
            self.logger.info(f"Created temporary directory: {tmpdir}")
            
            with zipfile.ZipFile(self.wheel_path, 'r') as zip_ref:
                zip_ref.extractall(tmpdir)
            
            for root, _, files in os.walk(tmpdir):
                for file in files:
                    file_path = os.path.join(root, file)
                    rel_path = os.path.relpath(file_path, tmpdir)
                    
                    if rel_path in self.exclude_files:
                        if not dry_run:
                            os.remove(file_path)
                        self.logger.info(f"{'Would remove' if dry_run else 'Removed'}: {rel_path}")
                    elif file.endswith('.so'):
                        if not dry_run:
                            self.apply_patches(file_path)
                        else:
                            self.logger.info(f"Would apply patches to: {rel_path}")
            
            if not dry_run:
                self.update_record_file(tmpdir)
                with zipfile.ZipFile(output_wheel, 'w', zipfile.ZIP_DEFLATED) as new_zip:
                    for root, _, files in os.walk(tmpdir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arc_name = os.path.relpath(file_path, tmpdir)
                            new_zip.write(file_path, arc_name)
                            self.logger.info(f"Added to new wheel: {arc_name}")
                self.logger.info(f"Repaired wheel saved as: {output_wheel}")
            else:
                self.logger.info("Dry run completed. No changes were made.")
                

def main():
    """
    Main function to run the wheel repair process.

    This function parses command-line arguments, sets up logging,
    reads the configuration file, and initiates the wheel repair process.

    Command-line Arguments:
        wheel_path (str): Path to the wheel file to repair.
        -o, --output-dir (str): Output directory for repaired wheels. Defaults to "repaired_wheels".
        --config (str): Path to YAML or JSON configuration file (required).
        --dry-run (flag): Perform a dry run without making changes.
        --log-level (str): Set the logging level. Choices are DEBUG, INFO, WARNING, ERROR, CRITICAL. Defaults to INFO.

    The function performs the following steps:
    1. Parse command-line arguments.
    2. Set up logging with the specified log level.
    3. Read and parse the configuration file.
    4. Create a WheelRepairer instance with the provided wheel path, output directory, and configuration.
    5. Initiate the repair process.

    Note: This function is the entry point of the script and is called when the script is run directly.
    """
    parser = argparse.ArgumentParser(description="Repair wheel files by removing and replacing libraries.")
    parser.add_argument("wheel_path", help="Path to the wheel file to repair")
    parser.add_argument("-o", "--output-dir", default="repaired_wheels", help="Output directory for repaired wheels")
    parser.add_argument("--config", required=True, help="Path to YAML or JSON configuration file")
    parser.add_argument("--dry-run", action="store_true", help="Perform a dry run without making changes")
    parser.add_argument("--log-level", choices=['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL'], 
                        default='INFO', help="Set the logging level")
    args = parser.parse_args()

    # Set up logging once with the specified log level
    log_level = getattr(logging, args.log_level)
    setup_logger(level=log_level)
    logger = get_logger()

    logger.debug(f"Logging level set to {args.log_level}")

    config = {}
    with open(args.config, 'r') as f:
        if args.config.endswith('.yaml') or args.config.endswith('.yml'):
            config = yaml.safe_load(f)
        else:
            config = json.load(f)

    repairer = WheelRepairer(args.wheel_path, args.output_dir, config)
    repairer.repair(dry_run=args.dry_run)

if __name__ == "__main__":
    """
    Script execution entry point.

    This conditional block ensures that the main() function is only executed
    when the script is run directly (not imported as a module).

    It serves as the entry point for the wheel repair utility, initiating
    the entire process of parsing arguments, setting up logging, and
    performing the wheel repair.
    """
    main()