from PIL import Image
import math
import os
import yaml
from colorama import Fore, Style


CONFIG_FILE = "config.yaml"


def write_yaml_with_comments(sample_img_path, yaml_path = CONFIG_FILE):
    """
    Writes a YAML configuration file with comments explaining each variable.

    Parameters:
        sample_img_path: The file path of one sample radar image from the given folder
        yaml_path (str): The file path where the YAML file will be written.
    """
    radar_img = Image.open(sample_img_path)

    (width, height) = radar_img.size

    center_offset = math.floor(height / 2)
    radar_zone_offset = math.floor(height * 0.05)
    radar_diameter = center_offset - radar_zone_offset

    yaml_content = f"""# Configuration for Radar Detection

radar_center: """ + str([center_offset, center_offset]) + """  # List of 2 integers: [x, y]
center_diameter: 9  # Integer

radar_zone: """ + str([radar_zone_offset, height - radar_zone_offset]) + """  # List of 2 integers: [x_min, x_max]
zone_diameter: """ + str(radar_diameter) + """  # Integer

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


max_velocity_color:  # List of two colors representing min and max velocities
  - [0, 224, 255]  # Min velocity color (RGB)
  - [255, 0, 0]    # Max velocity color (RGB)

blur_threshold: 29.5  # Float
area_fill_threshold: 45.0  # Float
narrow_fill_threshold: 36.0  # Float
complex_fill_threshold: 9.0  # Float
"""

    # Write the YAML content to the file
    with open(yaml_path, "w") as file:
        file.write(yaml_content)

    print(f"YAML file with comments written successfully at: {yaml_path}")


def check_input_folder(folder_path, is_default=True):
    """
    Checks if the specified folder path exists and contains valid radar image files.
    If the folder does not exist or contains no valid image files, an error message is printed.
    If `is_default` is True, it uses the first valid image found to write default configuration data.

    Parameters:
        folder_path (str): The path to the folder containing radar images.
        is_default (bool, optional): Whether to use the first valid image to write default data. Defaults to True.

    Returns:
        None
    """

    try:
        # Check if folder exists
        if not os.path.exists(folder_path):
            raise FileNotFoundError(f"Radar images folder path `{folder_path}` does not exist.")

        # Define valid image extensions
        valid_image_extensions = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}

        # List all files in the folder
        all_files = os.listdir(folder_path)

        # Filter valid image files
        image_files = [file for file in all_files if os.path.splitext(file)[1].lower() in valid_image_extensions]

        if not image_files:
            raise ValueError(f"No valid image files found in folder: {folder_path}.")

        if is_default:
            # Construct the full path of the first valid image file
            sample_image_path = os.path.join(folder_path, image_files[0])

            # Call function to write default data
            write_yaml_with_comments(sample_image_path)

    except FileNotFoundError as e:
        print(Fore.RED + f"[Error] {e}" + Style.RESET_ALL)
    except ValueError as e:
        print(Fore.RED + f"[Error] {e}" + Style.RESET_ALL)
    except Exception as e:  # Catch any other unexpected errors
        print(Fore.RED + f"[Unexpected Error] {e}" + Style.RESET_ALL)


def validate_config(yaml_path = CONFIG_FILE):
    """
    Validates a YAML file by ensuring all required keys exist and their values match the expected data types.

    Parameters:
        yaml_path (str): Path to the YAML file. Default value is CONFIG_FILE.

    Returns:
        bool: True if YAML is valid, False otherwise.
    """

    # Define the expected structure and data types
    expected_structure = {
        "radar_center": list,  # Expecting a list of 2 integers
        "center_diameter": int,
        "radar_zone": list,  # Expecting a list of 2 integers
        "zone_diameter": int,
        "color_velocity_pairs": list,  # List of lists containing tuples
        "max_velocity_color": list,  # List of lists
        "blur_threshold": float,
        "area_fill_threshold": float,
        "narrow_fill_threshold": float,
        "complex_fill_threshold": float
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
                if key in ["radar_center", "radar_zone"]:
                    if not (len(value) == 2 and all(isinstance(i, int) for i in value)):
                        print(Fore.RED + f"[Error] `{key}` should be a list of two integers." + Style.RESET_ALL)
                        return False

                elif key == "color_velocity_pairs":
                    if not all(isinstance(pair, list) and len(pair) == 2 and isinstance(pair[0], list) and isinstance(
                            pair[1], (int, float)) for pair in value):
                        print(
                            Fore.RED + f"[Error] `{key}` should be a list of [color, velocity] pairs." + Style.RESET_ALL)
                        return False

                elif key == "max_velocity_color":
                    if not all(
                            isinstance(color, list) and len(color) == 3 and all(isinstance(c, int) for c in color) for
                            color in value):
                        print(Fore.RED + f"[Error] `{key}` should be a list of RGB color values." + Style.RESET_ALL)
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
