"""
this file mainly provides public utility functions about folder process
"""
from PIL import Image, ImageDraw
from MesoDetect.DataIO.consts import GRAY_SCALE_UNIT
from MesoDetect.MesocycloneAnalysis.consts import MesocycloneInfo
from MesoDetect.DataIO.consts import DetectionResult
from datetime import datetime, timedelta
from MesoDetect.DataIO.consts import CONFIG_FILE
import math
import os
import yaml
from colorama import Fore, Style
from typing import Union, Optional, List, Tuple
from pathlib import Path
from MesoDetect.DataIO.consts import VALID_IMG_EXTENSION

"""
Utility Function: validate output image folder
"""
def check_output_folder(output_folder_path: Union[str, Path], current_folder_name: str) -> Optional[Path]:
    """
    Validates and prepares the output folder path, creating the specified subfolder if needed.

    Args:
        output_folder_path (Union[str, Path]): The base output directory path (can be a string or Path).
        current_folder_name (str): Name of the subdirectory to be created within the output folder.

    Returns:
        Optional[Path]: The full path to the created or existing subdirectory,
                        or None if an error occurred during folder creation.
    """
    try:
        output_path = Path(output_folder_path).expanduser().resolve()
        output_path.mkdir(parents=True, exist_ok=True)
        current_folder_path = output_path / current_folder_name
        if not os.path.exists(current_folder_path):
            os.makedirs(current_folder_path)
    except Exception as e:
        print(Fore.RED + f"[Error] Unexpected error: {e}" + Style.RESET_ALL)
        return None
    return current_folder_path


"""
Utility Function: extract images path from given folder
"""
def get_folder_image_paths(img_folder_path: Union[Path, str]) -> List[str]:
    """
    Retrieves the full paths of image files in a given folder.

    Args:
        img_folder_path (Union[Path, str]): Path to the folder containing image files.

    Returns:
        List[str]: A list of absolute Paths for valid image files in the folder.
    """
    # resolve input image folder path
    img_folder_path = Path(img_folder_path).expanduser().resolve()

    # extract all file names
    all_files = os.listdir(str(img_folder_path))

    # filter out image files
    image_files = [file for file in all_files if os.path.splitext(file)[1].lower() in VALID_IMG_EXTENSION]

    # iterate image file names
    image_paths = []
    for image_name in image_files:
        image_path = img_folder_path / image_name
        image_path = image_path.as_posix()
        image_paths.append(image_path)

    return image_paths



"""
This file contains functions that used to process input data and transforms then into
other styles.
"""


"""
Utility Function: visualizing process result image from gray color into original radar image color
"""
def visualize_result(folder_path: Path, gray_img: Image, result_name: str) -> str:
    """
    Generates a color visualization image from a grayscale radar image and saves it to disk.

    Args:
        folder_path (Path): The output directory where the visualization image will be saved.
        gray_img (Image): The grayscale radar image (PIL Image) to visualize.
        result_name (str): The filename (without extension) for the output image.

    Returns:
        str: The file path (as POSIX string) to the saved visualization image.
    """
    # Check result path
    visualize_result_path = folder_path / "visualization"
    if not os.path.exists(visualize_result_path):
        os.makedirs(visualize_result_path)

    # Create visualization result image
    visual_img = Image.new("RGB", gray_img.size, (0, 0, 0))
    visual_draw = ImageDraw.Draw(visual_img)

    # Iterate gray image
    radar_zone = get_radar_info("radar_zone")
    cv_pairs = get_color_bar_info("color_velocity_pairs")
    for x in range(radar_zone[0], radar_zone[1]):
        for y in range(radar_zone[0], radar_zone[1]):
            # Get current pixel value
            pixel_value = gray_img.getpixel((x, y))[0]
            # Calculate gray value index
            gray_value_index = round(1.0 * pixel_value / GRAY_SCALE_UNIT) - 1
            # Get actual color and draw
            if 0 <= gray_value_index <= len(cv_pairs) - 1:
                visual_draw.point((x, y), cv_pairs[gray_value_index][0])

    # Save visualization result image
    visualization_result_path = visualize_result_path / (result_name + ".png")
    visual_img.save(visualization_result_path)

    return visualization_result_path.as_posix()


def print_detection_result(result: DetectionResult):
    print("\n=== Detection Result ===")
    print(f"Station Number: {result['station_number']}")
    print(f"Scan Time (UTC): {result['scan_time']}")

    print("\nMesocyclone List:")
    for meso in result['meso_list']:
        print(f"\nStorm Number: {meso['storm_num']}")
        print(f"Logic Center: {meso['logic_center']}")
        print(f"Radar Distance: {meso['radar_distance']}")
        print(f"Radar Angle: {meso['radar_angle']}")
        print(f"Shear Value: {meso['shear_value']}")
        print(f"Negative Center: {meso['neg_center']}")
        print(f"Max Negative Velocity: {meso['neg_max_velocity']}")
        print(f"Positive Center: {meso['pos_center']}")
        print(f"Max Positive Velocity: {meso['pos_max_velocity']}")

    print("\nResult Image Paths:")
    for path in result['result_img_paths']:
        print(f"- {path}")




"""
Utility Function: packing detection result data into a single dictionary data
"""
def pack_detection_result(
        station_number: str,
        resolved_img_path: Path,
        refer_img: Image,
        meso_list: List[MesocycloneInfo],
        output_path: Path
) -> DetectionResult:
    """
    Packs the results of mesocyclone detection into a structured output and generates
    visualization images highlighting detected mesocyclones.

    Args:
        station_number (str): Radar station identifier.
        resolved_img_path (Path): Path to the original resolved radar image.
        refer_img (Image): Reference grayscale radar image (used to extract echo values).
        meso_list (List[MesocycloneInfo]): List of detected mesocyclone information.
        output_path (Path): Directory where visualization images will be saved.

    Returns:
        DetectionResult: A dictionary-like object containing detection metadata,
                         mesocyclone info, and paths to the generated images.
    """
    # Get scan time from resolved image path
    scan_time = resolved_img_path.as_posix().split("/")[-1].split("_")[4][:12]

    # Convert scan time into datetime type with UTC+8 format
    resolved_scan_time = datetime.strptime(scan_time, "%Y%m%d%H%M") + timedelta(hours=8)

    # Get basic data
    cv_pairs = get_color_bar_info("color_velocity_pairs")
    image_size = get_radar_info("image_size")

    # Iterate meso list for generating result images
    result_image_paths: List[str] = []
    for idx, meso_info in enumerate(meso_list, start=1):
        meso_result_img = Image.new("RGB", image_size, (0, 0, 0))
        meso_result_draw = ImageDraw.Draw(meso_result_img)
        neg_center = meso_info['neg_center']
        pos_center = meso_info['pos_center']
        range_diameter = round(math.sqrt((neg_center[0] - pos_center[0]) ** 2 + (neg_center[1] - pos_center[1]) ** 2))
        # Calculate mid-center of the meso pair
        mid_center_x = round((neg_center[0] + pos_center[0]) / 2)
        mid_center_y = round((neg_center[1] + pos_center[1]) / 2)
        # Draw detect area
        for x in range(mid_center_x - range_diameter, mid_center_x + range_diameter + 1):
            for y in range(mid_center_y - range_diameter, mid_center_y + range_diameter + 1):
                if math.sqrt((x - mid_center_x) ** 2 + (y - mid_center_y) ** 2) <= range_diameter:
                    # Extract echo value
                    echo_value = refer_img.getpixel((x, y))
                    echo_index = round(echo_value[0] / GRAY_SCALE_UNIT) - 1
                    if echo_index not in range(len(cv_pairs)):
                        continue
                    meso_result_draw.point((x, y), cv_pairs[echo_index][0])
        result_image_path = output_path / ("meso_detect" + str(idx) + ".png")
        meso_result_img.save(result_image_path)
        result_image_paths.append(result_image_path.as_posix())

    detection_result: DetectionResult = {
        "station_number": station_number,
        "scan_time": resolved_scan_time,
        "meso_list": meso_list,
        "result_img_paths": result_image_paths
    }

    return detection_result


"""
Utility Function: Read config data from radar config file
"""
def get_radar_info(var_name: str) -> Optional[Union[Tuple[int, int], List[int]]]:
    """
    Retrieves specific radar configuration data from a YAML configuration file.

    Args:
        var_name (str): Name of the radar configuration variable to retrieve.
                        Must be one of: "image_size", "radar_zone", "radar_center".

    Returns:
        Optional[Union[Tuple[int, int], List[int]]]: The requested configuration data,
        or None if the variable name is invalid or the config file cannot be read.
    """
    # Load YAML file
    with open(CONFIG_FILE, "r") as file:
        data = yaml.safe_load(file)

    if var_name == "image_size":
        width, height = data["image_size"]
        return width, height
    elif var_name == "radar_zone":
        return data["radar_zone"]
    elif var_name == "radar_center":
        return data["radar_center"]
    else:
        print(Fore.RED + f'[Error] Invalid var_name `{var_name}` for `get_radar_info`.' + Style.RESET_ALL)
        return None


"""
Utility Function: Read config data from radar config file
"""
def get_color_bar_info(var_name: str) -> Optional[List[Tuple[Tuple[int, int, int], float]]]:
    """
    Retrieves color bar configuration data from the YAML config file.

    Args:
        var_name (str): The name of the color bar variable to retrieve.
                        Currently only supports "color_velocity_pairs".

    Returns:
        Optional[List[Tuple[Tuple[int, int, int], float]]]: A list of color-velocity pairs,
        where each item is a (color RGB tuple, velocity value), or None if the variable name is invalid.
    """
    # Load YAML file
    with open(CONFIG_FILE, "r") as file:
        data = yaml.safe_load(file)

    if var_name == "color_velocity_pairs":
        cv_pairs_tuple = []
        for cv in data["color_velocity_pairs"]:
            cv_pairs_tuple.append(((cv[0][0], cv[0][1], cv[0][2]), cv[1]))
        return cv_pairs_tuple
    else:
        print(Fore.RED + f'[Error] Invalid var_name `{var_name}` for `get_color_bar_info`.' + Style.RESET_ALL)
        return None
