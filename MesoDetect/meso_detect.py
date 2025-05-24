import os
import time
from MesoDetect.DataIO import radar_config
from colorama import Fore, Style
from MesoDetect.DataIO.preprocessor import radar_image_preprocess
import re


def meso_detect(
        img_path: str,
        output_folder_path: str,
        station_num: str = "",
        enable_default_config: bool = True,
        enable_debug_mode: bool = False
):
    start = time.time()
    print("----------------------------------")
    # Station number validation
    # Check default station number from image name
    if station_num == "":
        # Default image name format: Z_RADR_I_Z9755_202404301154_P_DOR_SAD_V_5_115_15.755.png
        station_num = img_path.split("/")[-1].split("_")[3]
        print(f"[Info] Default station number from image path: {station_num}.")

    # Check station number format
    if not bool(re.fullmatch(r'Z\d{4}', station_num)):
        print(Fore.RED + f"[Error] Invalid station number: {station_num}." + Style.RESET_ALL)
        print(Fore.RED + "[Error] Detection setup failed." + Style.RESET_ALL)
        return None

    # Detection setup
    debug_folder_path = detection_setup(img_path, output_folder_path, station_num,
                                        enable_default_config, enable_debug_mode)
    if debug_folder_path is None:
        return None

    # Get gray image
    gray_img = radar_image_preprocess(img_path, station_num, enable_debug_mode, debug_folder_path)
    if gray_img is None:
        return None

    result_img_folder = output_folder_path + img_path.split("/")[-1].split(".")[0] + "/"
    if not os.path.exists(result_img_folder):
        os.makedirs(result_img_folder)
    gray_img.save(result_img_folder + "gray_img.png")

    end = time.time()
    duration = end - start
    print(f"[Info] Final duration of execution: {duration:.4f} seconds")
    return None


def detection_setup(img_path: str, output_folder_path: str, station_num: str, enable_default_config: bool = True, enable_debug_mode: bool = False):
    """
    Setting up mesocyclone detection configration.
    Args:
        img_path: path of radar image.
        output_folder_path: path of output folder.
        station_num: station number in string type.
        enable_default_config: boolean flat indicates if default config is enabled.
        enable_debug_mode: boolean flat indicates if debug mode is enabled.

    Returns:
        debug folder path if setup succeed.
        None if setup failed.
    """
    print("[Info] Start detection setup...")
    print(f"[Info] Input image path: {img_path}.")

    if enable_debug_mode:
        # Extract image name
        img_name = img_path.split("/")[-1].split(".")[0]
        print(f"[Debug] Image name: {img_name}.")
        # Get result folder path
        debug_images_folder_path = output_folder_path + img_name + "/"
        if not os.path.exists(debug_images_folder_path):
            os.makedirs(debug_images_folder_path)
    else:
        # Empty path indicate that debug mode is disabled
        debug_images_folder_path = ""

    print(f"[Info] Detection result image folder path: {debug_images_folder_path}.")

    # Set up radar image config
    setup_result = radar_config.setup_radar_img_config(img_path, False, enable_default_config)
    if not setup_result:
        print(Fore.RED + "[Error] Detection setup failed." + Style.RESET_ALL)
        return None

    print("[Info] Detection setup complete.")
    return debug_images_folder_path
