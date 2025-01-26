import os
import zipfile
from datetime import datetime, timezone
from pathlib import Path
import configparser
import sys
import time


# Function to read configuration from config.ini
def read_config(config_file):
    config = configparser.ConfigParser()
    config.read(config_file)
    
    # Iterate through each section and option in the config file
    for section in config.sections():
        for option in config.options(section):
            value = config.get(section, option)
            
            # Check if the value contains commas and split it into a list
            if ',' in value:
                value = [item.strip() for item in value.split(',')]  # Split by comma and strip spaces
            
            # Try to convert the value to an integer or float if possible
            if isinstance(value, str) and not isinstance(value, list):
                try:
                    value = config.getint(section, option)
                except ValueError:
                    try:
                        value = config.getfloat(section, option)
                    except ValueError:
                        pass  # Keep the value as string if it can't be converted

            # Dynamically create variables in the global scope
            globals()[option] = value


# Function to rotate the log file if it exceeds the size limit
def rotate_log_file():
    """Rotate the log file if it exceeds the size limit."""
    global log_file_name  # To allow modifying the global variable log_file_name
    
    log_file_path = os.path.join(output_directory, log_file_name)  # Full path of the current log file
    if os.path.exists(log_file_path):
        file_size = os.path.getsize(log_file_path)
        if file_size >= max_log_size:
            # If the log file exceeds the limit, rename it with a timestamp
            timestamp = time.strftime("[%Y-%m-%d %H:%M:%S] ")
            new_log_name = f"{log_file_name}_{timestamp}"
            new_log_path = os.path.join(output_directory, new_log_name)
            
            # Rename the current log file to include the timestamp
            os.rename(log_file_path, new_log_path)
            print(f"Log file rotated: {new_log_path}")
            
            # Create a new log file with the original name
            with open(log_file_path, 'w') as new_log_file:
                new_log_file.write("New log file created\n")
            
            # Update the global log_file_name to the new log name (without timestamp)
            log_file_name = new_log_name
            
            # Return the new log file name
            return new_log_name
    return log_file_name  # No rotation occurred, return original name

# Function to write a message to the log file
def write_log(message):
    """Write a message to the log file."""
    # Rotate log if necessary before writing the new message
    updated_log_file_name = rotate_log_file()
    
    # Get the log file path after potential rotation
    log_file_path = os.path.join(output_directory, updated_log_file_name)
    
    # Write the log message to the log file
    with open(log_file_path, 'a') as log_file:
        log_file.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {message}\n")
        print(f"Logged: {message}")

def write_log_noTS(message):
    """Write a message to the log file."""
    # Rotate log if necessary before writing the new message
    updated_log_file_name = rotate_log_file()
    
    # Get the log file path after potential rotation
    log_file_path = os.path.join(output_directory, updated_log_file_name)
    
    # Write the log message to the log file
    with open(log_file_path, 'a') as log_file:
        log_file.write(f"{message}\n")
        print(f"Logged: {message}")

def print_header():
    # Get the current timestamp
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    
    # Log a decorated header line with asterisks
    write_log_noTS(f"{'*' * 80}")
    write_log_noTS(f"Run of the \"{timestamp}\"")
    write_log_noTS(f"{'*' * 80}")
    '''
    for key, value in {key: value for key, value in locals().items() if not key.startswith('__')}.items():
        # Add asterisks before and after each key-value pair for decoration
        write_log(f"* {key}: {value} *")
    '''
    # Log a closing line of asterisks
    write_log_noTS(f"{'*' * 80}")
    
def create_incremental_archive(folder_path, output_dir):
    """
    Create an incremental archive for a single folder and store it in the given output directory,
    including subfolders and preserving the directory structure.
    
    Args:
        folder_path (str): The path to the folder to archive.
        output_dir (str): The root output directory where the archive will be stored.
    """
    # Ensure the folder exists
    if not os.path.isdir(folder_path):
        write_log(f"The folder {folder_path} does not exist.")
        return
    
    # Ensure the output directory exists
    if not os.path.isdir(output_dir):
        write_log(f"The output directory {output_dir} does not exist. Creating it.")
        os.makedirs(output_dir)
    
    # Create the archive name based on the folder name (without timestamp)
    folder_name = os.path.basename(folder_path)
    archive_name = f"{folder_name}.zip"  # Always use the same name to overwrite

    # Full path for the archive in the specified output directory
    archive_path = os.path.join(output_dir, archive_name)
    
    try:
        # Open the archive in append mode (to avoid overwriting it)
        with zipfile.ZipFile(archive_path, 'a', zipfile.ZIP_DEFLATED) as zipf:
            # Track the files already in the archive by their relative path
            existing_files_in_archive = {info.filename for info in zipf.infolist()}
            # Walk through the entire folder (including subfolders)
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    file_mod_time = os.path.getmtime(file_path)
                    
                    # Calculate the relative path for the file (to maintain folder structure)
                    relative_path = os.path.relpath(file_path, folder_path)
                    # Split the relative path into the file name and extension
                    file_name, file_extension = os.path.splitext(relative_path)
                    # Get the modification time and format it
                    timestamp = datetime.fromtimestamp(file_mod_time, tz=timezone.utc).strftime('%Y%m%d_%H%M%S')
                    # Include the relative path in the modified filename to ensure uniqueness
                    modified_filename = f"{file_name}_{timestamp}{file_extension}"
      
                    # Check if the modified file has already been added by comparing the full relative path
                    if modified_filename in existing_files_in_archive:
                        write_log(f"Warning: File {modified_filename} already exists in the archive. Skipping...")
                        continue  # Skip adding this file
                    
                    # Write the file to the archive, using its relative path within the zip archive
                    arcname = modified_filename

                    # Write the file to the archive
                    zipf.write(file_path, arcname=arcname)
                    existing_files_in_archive.add(modified_filename)
                    write_log(f"Added modified file to archive: {file} (modified as {modified_filename})")
        
        write_log(f"Archive updated successfully: {archive_path}")
        write_log_noTS("------")    
    except Exception as e:
        write_log(f"An error occurred while creating the archive for {folder_path}: {e}")

# Function to get the file path (works for both Python script and compiled executable)
def get_file_path(file_name):
    # If running from a bundled exe, the file will be in same folder as the exe
    if getattr(sys, 'frozen', False):
        # Running as a bundled exe, get the path to the directory of the exe
        exe_dir = os.path.dirname(sys.executable)
        return os.path.join(exe_dir, file_name)
    else:
        # Running as a Python script
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), file_name)

# Read configuration from config.ini
read_config(get_file_path('config.ini'))
# Print header into logs
print_header()
# Process each folder in the list
for folder_path in folder_paths:
    create_incremental_archive(folder_path.strip(), output_directory)
write_log(f"########## All archives are succesfully updated ##########")
