import time
from colorama import Fore, Style
from MesoDetect.DataIO.data_config import setup_config
from MesoDetect.DataIO.preprocessor import radar_image_preprocess
from MesoDetect.RadarDenoise.denoise import radar_denoise
from MesoDetect.DataIO.utils import visualize_result, pack_detection_result, print_detection_result
from MesoDetect.ImmerseSimulation.peak_detector import get_extrema_regions
from MesoDetect.MesocycloneAnalysis.meso_analysis import opposite_extrema_analysis
from typing import Union, Optional, List, Callable
from pathlib import Path
from MesoDetect.DataIO.consts import DetectionResult
from MesoDetect.DataIO.utils import get_folder_image_paths, check_output_folder


def meso_detect_with_progress(
        img_path: Path,
        output_folder_path: Path,
        update_progress: Callable[[int, int], None]
) -> Optional[List[DetectionResult]]:
    total_steps = 5
    step = 0

    # 1. Setup config
    setup_result = setup_config(img_path, output_folder_path, "", True)
    if setup_result is None:
        return None
    station_num, resolved_img_path, output_path = setup_result
    step += 1
    update_progress(step, total_steps)

    # 2. Preprocess image
    gray_img = radar_image_preprocess(resolved_img_path, station_num, output_path, False)
    if gray_img is None:
        return None
    step += 1
    update_progress(step, total_steps)

    # 3. Denoise
    unfold_img = radar_denoise(gray_img, output_path, False)
    if unfold_img is None:
        return None
    step += 1
    update_progress(step, total_steps)

    # 4. Immerse simulation
    immerse_result = get_extrema_regions(unfold_img, output_path, False)
    if immerse_result is None:
        return None
    neg_regions, pos_regions = immerse_result
    step += 1
    update_progress(step, total_steps)

    # 5. Mesocyclone analysis
    meso_list = opposite_extrema_analysis(unfold_img, neg_regions, pos_regions, output_path, False)
    if meso_list is None:
        return None

    result = pack_detection_result(station_num, resolved_img_path, unfold_img, meso_list, output_path)
    step += 1
    update_progress(step, total_steps)

    print([result])
    return [result]




def meso_detect(
        img_path: Union[str, Path],
        output_folder_path: Union[str, Path],
        enable_debug_mode: bool = False
) -> Optional[list[DetectionResult]]:
    start = time.time()
    print("----------------------------------")
    print("[Info] Start Mesocyclone detection.")
    print(f"[Info] Original Image path: {img_path}.")

    # Current project version only allow default config radar image data
    enable_default_config: bool = True
    # And extract station numbe from formatted image name
    station_num: str = ""

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


def meso_batch_detect(
        img_folder_path: Union[str, Path],
        output_folder_path: Union[str, Path],
        enable_debug_mode: bool = False
) -> Optional[list[DetectionResult]]:
    start = time.time()
    print("----------------------------------")
    print("[Info] Start mesocyclone batch detection.")
    print(f"[Info] Original input folder path: {img_folder_path}.")

    # Current project version only allow default config radar image data
    enable_default_config: bool = True
    # And extract station numbe from formatted image name
    station_num: str = ""

    # Get valid image paths from given input folder
    radar_img_paths = get_folder_image_paths(img_folder_path)

    # Check extraction result
    if len(radar_img_paths) == 0:
        print(Fore.RED + "[Error] No valid image file in given directory." + Style.RESET_ALL)
        return None

    # Get sample image for config setup
    sample_img_path = radar_img_paths[0]
    setup_result = setup_config(sample_img_path, output_folder_path, station_num, enable_default_config)

    # Check setup result
    if setup_result is None:
        print(Fore.RED + "[Error] Detection config data setup failed." + Style.RESET_ALL)
        return None
    station_num, _, _ = setup_result

    # Batch process
    detection_results: List[DetectionResult] = []
    for img_num, radar_img_path in enumerate(radar_img_paths, start=1):
        print(f"---[Info] Image {img_num} Mesocyclone Detection:")
        batch_start = time.time()

        # Extract image name from image path
        process_result_folder_name = radar_img_path.as_posix().split("/")[-1].split(".")[0]
        # Create a folder with the extracted image name under given output directory
        result_output_path = check_output_folder(output_folder_path, process_result_folder_name)
        if result_output_path is None:
            print(Fore.RED + "[Error] Create result output folder failed." + Style.RESET_ALL)
            return None
        print(f"[Info] Detection result image folder path: {result_output_path}.")

        detection_result = detect_mesocyclone(radar_img_path, result_output_path, station_num, enable_debug_mode)
        if detection_result is None:
            print(Fore.RED + "[Error] Meso detection process failed." + Style.RESET_ALL)
            return None
        batch_end = time.time()
        batch_duration = batch_end - batch_start
        print(f"---[Info] Image {img_num} Mesocyclone Complete.")
        print(f"---[Info] Duration of batch execution: {batch_duration:.4f} seconds")
        detection_results.append(detection_result)

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
    if enable_debug_mode:
        print_detection_result(detection_result)

    return detection_result
