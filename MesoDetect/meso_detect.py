import time
from MesoDetect.DataIO.radar_config import validate_station_number, detection_setup
from colorama import Fore, Style
from MesoDetect.DataIO.preprocessor import radar_image_preprocess
from MesoDetect.RadarDenoise.denoise import radar_denoise
from MesoDetect.DataIO.data_transformer import visualize_result, pack_detection_result
from MesoDetect.ImmerseSimulation.peak_detector import get_extrema_regions
from MesoDetect.MesocycloneAnalysis.meso_analysis import opposite_extrema_analysis
from typing import Union
from pathlib import Path

"""
    input path(including folder path and file path) handling:
    user can provide path format from different OS or use Python Path
    project will process these paths. Internal representation use the Linux string format (.as_poxis())
    and when need to join path with a directory then still convert to Python Path so that no need to check "/"
    at the end of the path
    File path:
        User either provide a string type of valid file path (window format or linux format) or Python Pathlib Path
        Program will convert the path to Python Pathlib Path as internal representation, which is convenient to join file name
        or directory and save output image.
        Extracting key info from image name, first convert the path from Python Pathlib Path into string then use string
        process function
"""

def meso_detect(
        img_path: Union[str, Path],
        output_folder_path: Union[str, Path],
        station_num: str = "",
        enable_default_config: bool = True,
        enable_debug_mode: bool = False
):
    start = time.time()
    print("----------------------------------")
    print(f"[Debug] Original Image path: {img_path}.")

    # Check station number, extract image name from resolved image path and get the resolved path
    validation_result = validate_station_number(station_num, img_path)
    if validation_result is None:
        print(Fore.RED + "[Error] Station number check failed." + Style.RESET_ALL)
        return None
    # Extract station number and resolved image path when executing successfully
    station_num, resolved_img_path = validation_result
    print(f"[Debug] Resolve Image path: {resolved_img_path}")

    # Generate radar image configration data and check output folder path
    output_path = detection_setup(resolved_img_path, output_folder_path, enable_default_config)
    if output_path is None:
        return None
    print(f"[Debug] Output path: {output_path}")

    # Get gray image
    gray_img = radar_image_preprocess(resolved_img_path, station_num, output_path, enable_debug_mode)
    if gray_img is None:
        print(Fore.RED + "[Error] Radar image preprocessing failed." + Style.RESET_ALL)
        return None

    # Get denoised image
    unfold_img = radar_denoise(gray_img, output_path, enable_debug_mode)
    if unfold_img is None:
        print(Fore.RED + "[Error] Radar denoise process failed." + Style.RESET_ALL)
        return None

    if enable_debug_mode:
        visualize_result(output_path, unfold_img, "unfold")

    immerse_simulation_result = get_extrema_regions(unfold_img, output_path, enable_debug_mode)
    if immerse_simulation_result is None:
        print(Fore.RED + "[Error] Immerse simulation process failed." + Style.RESET_ALL)
        return None

    neg_extrema_regions, pos_extrema_regions = immerse_simulation_result

    mesocyclone_list = opposite_extrema_analysis(unfold_img, neg_extrema_regions, pos_extrema_regions, output_path, enable_debug_mode)
    if mesocyclone_list is None:
        print(Fore.RED + "[Error] Mesocyclone analysis process failed." + Style.RESET_ALL)
        return None

    detection_result = pack_detection_result(station_num, resolved_img_path, unfold_img, mesocyclone_list, output_path)
    detection_results = [detection_result]

    end = time.time()
    duration = end - start
    print(f"[Info] Final duration of execution: {duration:.4f} seconds")
    return detection_results

