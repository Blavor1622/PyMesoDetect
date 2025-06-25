import time
from colorama import Fore, Style
from MesoDetect.DataIO.data_config import setup_config
from MesoDetect.DataIO.preprocessor import radar_image_preprocess
from MesoDetect.RadarDenoise.denoise import radar_denoise
from MesoDetect.DataIO.utils import visualize_result, pack_detection_result, print_detection_result
from MesoDetect.ImmerseSimulation.peak_detector import get_extrema_regions
from MesoDetect.MesocycloneAnalysis.meso_analysis import opposite_extrema_analysis
from typing import Union, Optional
from pathlib import Path
from MesoDetect.DataIO.consts import DetectionResult

def meso_detect(
        img_path: Union[str, Path],
        output_folder_path: Union[str, Path],
        station_num: str = "",
        enable_default_config: bool = True,
        enable_debug_mode: bool = False
) -> Optional[list[DetectionResult]]:
    start = time.time()
    print("----------------------------------")
    print(f"[Info] Original Image path: {img_path}.")

    setup_result = setup_config(img_path, output_folder_path, station_num, enable_default_config)
    if setup_result is None:
        print(Fore.RED + "[Error] Detection config data setup failed." + Style.RESET_ALL)
        return None
    station_num, resolved_img_path, output_path = setup_result

    detection_result = detect_mesocyclone(resolved_img_path, output_path, station_num, enable_debug_mode)
    if detection_result is None:
        print(Fore.RED + "[Error] Meso detection process failed." + Style.RESET_ALL)
        return None

    detection_results = [detection_result]

    end = time.time()
    duration = end - start
    print(f"[Info] Final duration of execution: {duration:.4f} seconds")
    return detection_results


def detect_mesocyclone(
        resolved_img_path: Path,
        output_path: Path,
        station_num: str = "",
        enable_debug_mode: bool = False
) -> Optional[DetectionResult]:
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

    mesocyclone_list = opposite_extrema_analysis(unfold_img, neg_extrema_regions, pos_extrema_regions, output_path,
                                                 enable_debug_mode)
    if mesocyclone_list is None:
        print(Fore.RED + "[Error] Mesocyclone analysis process failed." + Style.RESET_ALL)
        return None

    detection_result = pack_detection_result(station_num, resolved_img_path, unfold_img, mesocyclone_list, output_path)
    print_detection_result(detection_result)

    return detection_result
