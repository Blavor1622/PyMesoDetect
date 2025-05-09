from PIL import Image
import math
from colorama import Fore, Style
import yaml
import os
from MesoDetect.DataIO.consts import CONFIG_FILE, VALID_IMG_EXTENSION


""" this is interface for radar image configration data setting up """
def setup_radar_img_config(data_path: str, is_folder: bool = False, enable_default_config: bool = True):
    # Check given data path is a folder or single image
    sample_img_path = data_path
    if is_folder:
        # Check folder data
        sample_img_path = check_input_folder(data_path)

    # From parameter decide whether to update default image config data or not
    if enable_default_config:
        write_default_config(sample_img_path)

    # Validate config file
    validate_radar_config()


"""
    The following functions is internal dependency logic function
"""
def write_default_config(sample_img_path, yaml_path = CONFIG_FILE):
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
image_size: """ + str([width, height]) + """ # size of radar image: [width, height]

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

blur_threshold: 15.5  # Float
area_fill_threshold: 500.0  # Float
narrow_fill_threshold: 48.0  # Float
"""

    # Write the YAML content to the file
    with open(yaml_path, "w") as file:
        file.write(yaml_content)

    print(f"[Info] Default YAML file generated successfully at: {yaml_path}")


def check_input_folder(folder_path):
    """
    Checks if the specified folder path exists and contains valid radar image files.
    If the folder does not exist or contains no valid image files, an error message is printed.
    If `is_default` is True, it uses the first valid image found to write default configuration data.

    Parameters:
        folder_path (str): The path to the folder containing radar images.

    Returns:
        None
    """

    try:
        # Check if folder exists
        if not os.path.exists(folder_path):
            raise FileNotFoundError(f"Radar images folder path `{folder_path}` does not exist.")

        # List all files in the folder
        all_files = os.listdir(folder_path)

        # Filter valid image files
        image_files = [file for file in all_files if os.path.splitext(file)[1].lower() in VALID_IMG_EXTENSION]

        if not image_files:
            raise ValueError(f"No valid image files found in folder: {folder_path}.")

        # Get a sample image path from input folder
        sample_image_path = os.path.join(folder_path, image_files[0])

        return sample_image_path

    except FileNotFoundError as e:
        print(Fore.RED + f"[Error] {e}" + Style.RESET_ALL)
    except ValueError as e:
        print(Fore.RED + f"[Error] {e}" + Style.RESET_ALL)
    except Exception as e:  # Catch any other unexpected errors
        print(Fore.RED + f"[Unexpected Error] {e}" + Style.RESET_ALL)


def validate_radar_config(yaml_path = CONFIG_FILE):
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
        "center_diameter": int,
        "radar_zone": list,  # Expecting a list of 2 integers
        "zone_diameter": int,
        "color_velocity_pairs": list,  # List of lists containing tuples
        "blur_threshold": float,
        "area_fill_threshold": float,
        "narrow_fill_threshold": float,
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


"""
    The following functions is for internal script reading radar config data
"""

def get_half_color_bar(mode):
    # Load YAML file
    with open(CONFIG_FILE, "r") as file:
        data = yaml.safe_load(file)

    half_len = int(len(data["color_velocity_pairs"]) / 2)
    if mode == 'neg':
        neg_color_scales = []
        for idx in range(half_len - 1, -1, -1):
            neg_color_scales.append(tuple(data["color_velocity_pairs"][idx][0]))
        return neg_color_scales
    elif mode == 'pos':
        pos_color_scales = []
        for idx in range(half_len, len(data["color_velocity_pairs"])):
            pos_color_scales.append(tuple(data["color_velocity_pairs"][idx][0]))
        return pos_color_scales
    else:
        print(Fore.RED + f"[Error] Invalid mode code: `{mode}` for `get_half_color_bar`." + Style.RESET_ALL)
        return


def get_radar_info(var_name):
    # Load YAML file
    with open(CONFIG_FILE, "r") as file:
        data = yaml.safe_load(file)

    if var_name == "image_size":
        return tuple(data["image_size"])
    elif var_name == "radar_zone":
        return data["radar_zone"]
    elif var_name == "radar_center":
        return data["radar_center"]
    elif var_name == "center_diameter":
        return data["center_diameter"]
    elif var_name == "zone_diameter":
        return data["zone_diameter"]
    else:
        print(Fore.RED + f'[Error] Invalid var_name `{var_name}` for `get_radar_info`.' + Style.RESET_ALL)
        return


def get_color_bar_info(var_name):
    # Load YAML file
    with open(CONFIG_FILE, "r") as file:
        data = yaml.safe_load(file)

    if var_name == "color_velocity_pairs":
        cv_pairs_tuple = []
        for cv in data["color_velocity_pairs"]:
            cv_pairs_tuple.append((tuple(cv[0]), cv[1]))
        return cv_pairs_tuple
    else:
        print(Fore.RED + f'[Error] Invalid var_name `{var_name}` for `get_color_bar_info`.' + Style.RESET_ALL)
        return


def get_threshold(var_name):
    # Load YAML file
    with open(CONFIG_FILE, "r") as file:
        data = yaml.safe_load(file)

    if var_name == "blur_threshold":
        return data["blur_threshold"]
    elif var_name == "area_fill_threshold":
        return data["area_fill_threshold"]
    elif var_name == "narrow_fill_threshold":
        return data["narrow_fill_threshold"]
    elif var_name == "complex_fill_threshold":
        return data["complex_fill_threshold"]
    else:
        print(Fore.RED + f'[Error] Invalid var_name `{var_name}` for `get_threshold`.' + Style.RESET_ALL)
        return


"""
    config data reading usage demonstration
"""
# if __name__ == '__main__':
#     # Print values to verify
#     print("Radar size:", get_radar_info("image_size"))
#     print("Radar Center:", get_radar_info("radar_center"))
#     print("Center Diameter:", get_radar_info("center_diameter"))
#     print("Radar Zone:", get_radar_info("radar_zone"))
#     print("Zone Diameter:", get_radar_info("zone_diameter"))
#     print("Color-Velocity Pairs:", get_color_bar_info("color_velocity_pairs"))
#     print("Blur Threshold:", get_threshold("blur_threshold"))
#     print("Area Fill Threshold:", get_threshold("area_fill_threshold"))
#     print("Narrow Fill Threshold:", get_threshold("narrow_fill_threshold"))
#
#     print("neg_color_scales: ",get_half_color_bar("neg"))
#     print("pos_color_scales: ",get_half_color_bar("pos"))

