"""
This file provides functions that process input original radar image
and generate a radar image configration data file, also provides functions
to read configration data
"""
from PIL import Image
import math
from colorama import Fore, Style
import yaml
import re
import os
from MesoDetect.DataIO.consts import CONFIG_FILE
from MesoDetect.DataIO.utils import check_output_folder
from typing import Union, Optional, Tuple
from pathlib import Path


"""
Public Interface for setting up data configration
"""
def setup_config(
        img_path: Union[str, Path],
        output_folder_path: Union[str, Path],
        station_num: str = "",
        enable_default_config: bool = True,
) -> Optional[Tuple[str, Path, Path]]:
    """
    Set up detetion configuration data, including resolving original image path, creating output directory, extracting
    station number, writing and validating radar image configuration data.
    Args:
        img_path: original input image path
        output_folder_path: given output path
        station_num: radar station number
        enable_default_config: bool flag for enabling default radar image config

    Returns:
        resolved station number, resolved image path and output directory path if processing successfully,
        None otherwise.
    """
    print("[Info] Start setting up data configuration...")
    # Resolve original input image path, transform into Path type
    resolved_image_path = Path(img_path).expanduser().resolve()
    # Get String type image path for string process
    resolved_img_path_str = resolved_image_path.as_posix()
    print(f"[Info] Resolved image path (str): {resolved_img_path_str}")
    # If use default station number extracted from formatted image name
    if station_num == "":
        # Default image name format: Z_RADR_I_Z9755_202404301154_P_DOR_SAD_V_5_115_15.755.png
        station_num = resolved_img_path_str.split("/")[-1].split("_")[3]
        print(f"[Info] Default station number from image path: {station_num}.")

    # Check station number format
    if not bool(re.fullmatch(r'Z\d{4}', station_num)):
        print(Fore.RED + f"[Error] Invalid station number: {station_num}." + Style.RESET_ALL)
        return None

    # Extract image name from image path
    process_result_folder_name = resolved_img_path_str.split("/")[-1].split(".")[0]
    # Create a folder with the extracted image name under given output directory
    result_output_path = check_output_folder(output_folder_path, process_result_folder_name)
    if result_output_path is None:
        print(Fore.RED + "[Error] Create result output folder failed." + Style.RESET_ALL)
        return None
    print(f"[Info] Detection result image folder path: {result_output_path}.")

    # Check if use default radar image configurataion
    if enable_default_config:
        write_result = write_default_config(resolved_img_path_str)
        if not write_result:
            print(Fore.RED + "[Error] Writing default configration data failed." + Style.RESET_ALL)
            return None

    # Validate config file
    validation_result = validate_radar_config()
    if not validation_result:
        print(Fore.RED + "[Error] Validating radar image configration data failed." + Style.RESET_ALL)
        return None
    print("[Info] Setting up data configuration complete.")
    return station_num, resolved_image_path, result_output_path


"""
Logic Implementation Functon: output default radar image config file
"""
def write_default_config(sample_img_path: str, yaml_path: str = CONFIG_FILE):
    """
    Writes a YAML configuration file with comments explaining each variable.

    Parameters:
        sample_img_path: The file path of one sample radar image from the given folder
        yaml_path (str): The file path where the YAML file will be written.
    Returns:
        True if default config file generated successfully.
        False if default config file generated failed.
    """
    try:
        radar_img = Image.open(sample_img_path)

        (width, height) = radar_img.size

        center_offset = math.floor(height / 2)
        radar_zone_offset = math.floor(height * 0.05)

        yaml_content = f"""# Configuration for Radar Detection
    image_size: """ + str([width, height]) + """ # size of radar image: [width, height]
    
    radar_center: """ + str([center_offset, center_offset]) + """  # List of 2 integers: [x, y]
    
    radar_zone: """ + str([radar_zone_offset, height - radar_zone_offset]) + """  # List of 2 integers: [x_min, x_max]
        
    color_velocity_pairs:  # List of color-velocity pairs
      - - [0, 224, 255]  # RGB Color [R, G, B] (List of 3 integers)
        - -27.5          # Velocity (Float)
      - - [0, 128, 255]
        - -23.5
      - - [50, 0, 150]
        - -17.5
      - - [0, 251, 144]
        - -12.5
      - - [0, 187, 144]
        - -7.5
      - - [0, 143, 0]
        - -3
      - - [205, 192, 159]
        - -0.5
      - - [255, 255, 255]
        - 0.5
      - - [248, 135, 0]
        - 3
      - - [255, 207, 0]
        - 7.5
      - - [255, 255, 0]
        - 12.5
      - - [174, 0, 0]
        - 17.5
      - - [208, 112, 0]
        - 23.5
      - - [255, 0, 0]
        - 27.5
    
    """
    except Exception as e:
        print(Fore.RED + f"[Error] Unexcepted: {e}" + Style.RESET_ALL)
        return False

    # Write the YAML content to the file
    with open(yaml_path, "w") as file:
        file.write(yaml_content)

    print(f"[Info] Default radar config file generated successfully at: {yaml_path}")
    return True


"""
Logic Implementation Functon: validate radar image config file format
"""
def validate_radar_config(yaml_path: str = CONFIG_FILE):
    """
    Validates a YAML file by ensuring all required keys exist and their values match the expected data types.

    Parameters:
        yaml_path (str): Path to the YAML file. Default value is CONFIG_FILE.

    Returns:
        bool: True if YAML is valid, False otherwise.
    """

    # Define the expected structure and data types
    expected_structure = {
        "image_size": list, # Expecting a list of 2 integers
        "radar_center": list,  # Expecting a list of 2 integers
        "radar_zone": list,  # Expecting a list of 2 integers
        "color_velocity_pairs": list,  # List of lists containing tuples
    }

    # Check if the file exists
    if not os.path.exists(yaml_path):
        print(Fore.RED + f"[Error] YAML file `{yaml_path}` does not exist." + Style.RESET_ALL)
        return False

    try:
        # Load YAML file
        with open(yaml_path, "r") as file:
            data = yaml.safe_load(file)

        # Check for missing keys and type mismatches
        for key, expected_type in expected_structure.items():
            if key not in data:
                print(Fore.RED + f"[Error] Missing key: `{key}` in the YAML file." + Style.RESET_ALL)
                return False

            value = data[key]

            # Handle lists with specific structures
            if isinstance(value, list):
                if key in ["image_size", "radar_center", "radar_zone"]:
                    if not (len(value) == 2 and all(isinstance(i, int) for i in value)):
                        print(Fore.RED + f"[Error] `{key}` should be a list of two integers." + Style.RESET_ALL)
                        return False

                elif key == "color_velocity_pairs":
                    if not all(isinstance(pair, list) and len(pair) == 2 and isinstance(pair[0], list) and isinstance(
                            pair[1], (int, float)) for pair in value):
                        print(
                            Fore.RED + f"[Error] `{key}` should be a list of [color, velocity] pairs." + Style.RESET_ALL)
                        return False

            elif not isinstance(value, expected_type):
                print(
                    Fore.RED + f"[Error] `{key}` has an invalid type. Expected `{expected_type.__name__}`, but got `{type(value).__name__}`." + Style.RESET_ALL)
                return False

        print(Fore.GREEN + "[Info] YAML config file passes check." + Style.RESET_ALL)
        return True

    except yaml.YAMLError as e:
        print(Fore.RED + f"[Error] Invalid YAML syntax: {e}" + Style.RESET_ALL)
        return False
