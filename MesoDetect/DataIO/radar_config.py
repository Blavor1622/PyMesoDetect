from PIL import Image
import math
from colorama import Fore, Style
import yaml
import os
from MesoDetect.DataIO.consts import CONFIG_FILE, VALID_IMG_EXTENSION


""" this is interface for radar image configration data setting up """
def setup_radar_img_config(
        data_path: str,
        is_folder: bool = False,
        enable_default_config: bool = True
):
    """
    Setting up radar image configration data.
    Args:
        data_path: path of radar image data whether is a single image path or a folder path.
        is_folder: boolean value flat that indicate whether the input data path is a folder path or not.
        enable_default_config: boolean flat that indicate whether the default config is enabled or not.

    Returns:
        Boolean value True if setup completed successfully.
        False if setup failed.
    """
    print("[Info] Setting up radar image config data...")
    # Check given data path is a folder or single image
    sample_img_path = data_path
    if is_folder:
        # Check folder data
        sample_img_path = check_input_folder(data_path)
        if sample_img_path is None:
            print(Fore.RED + "[Error] Radar image config data setup failed." + Style.RESET_ALL)
            return False

    # From parameter decide whether to update default image config data or not
    if enable_default_config:
        write_result = write_default_config(sample_img_path)
        if not write_result:
            print(Fore.RED + "[Error] Radar image config data setup failed." + Style.RESET_ALL)
            return False

    # Validate config file
    validation_result = validate_radar_config()
    if not validation_result:
        print(Fore.RED + "[Error] Radar image config data setup failed." + Style.RESET_ALL)
        return False
    print("[Info] Radar image config data setup complete.")
    return True


"""
    The following functions is internal dependency logic function
"""
def check_input_folder(folder_path):
    """
    Checks if the specified folder path exists and contains valid radar image files.
    If the folder does not exist or contains no valid image files, an error message is printed and None is returned.

    Parameters:
        folder_path (str): The path to the folder containing radar images.

    Returns:
        Sample radar image path or None when exception is raised.
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
        return None
    except ValueError as e:
        print(Fore.RED + f"[Error] {e}" + Style.RESET_ALL)
        return None
    except Exception as e:  # Catch any other unexpected errors
        print(Fore.RED + f"[Error] Unexcepted: {e}" + Style.RESET_ALL)
        return None


def write_default_config(sample_img_path, yaml_path = CONFIG_FILE):
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


"""
    The following functions is for internal script reading radar config data
"""
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
    else:
        print(Fore.RED + f'[Error] Invalid var_name `{var_name}` for `get_radar_info`.' + Style.RESET_ALL)
        return None


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
        return None


"""
    config data reading usage demonstration
"""
# if __name__ == '__main__':
#     # Print values to verify
#     print("Radar size:", get_radar_info("image_size"))
#     print("Radar Center:", get_radar_info("radar_center"))
#     print("Radar Zone:", get_radar_info("radar_zone"))
#     print("Color-Velocity Pairs:", get_color_bar_info("color_velocity_pairs"))
#
#     print("neg_color_scales: ",get_half_color_bar("neg"))
#     print("pos_color_scales: ",get_half_color_bar("pos"))

