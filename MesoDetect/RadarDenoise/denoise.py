from PIL import Image
import time
from colorama import Fore, Style
from MesoDetect.RadarDenoise import layer_analysis, dependencies, velocity_integrate, velocity_unfold
from MesoDetect.DataIO.utils import check_output_folder
from MesoDetect.RadarDenoise.consts import CURRENT_DEBUG_RESULT_FOLDER
from pathlib import Path
from typing import Optional

"""
    layer denoise interface
"""
def radar_denoise(
        preprocessed_img: Image,
        output_path: Path,
        enable_debug: bool = False
) -> Optional[Image]:
    """
    Apply velocity layer analysis to denoise and velocity unfolding
    Args:
        preprocessed_img: preprocessed radar image in internal gray format
        output_path: output path from current radar image process result
        enable_debug: boolean flag enabling debug mode for saving analysis result image

    Returns: denoised image in PIL.Image type, None otherwise
    """
    start = time.time()
    print("[Info] Start radar denoise process...")
    debug_output_path = output_path
    if enable_debug:
        debug_output_path = check_output_folder(output_path, CURRENT_DEBUG_RESULT_FOLDER)
        if debug_output_path is None:
            print(Fore.RED + "[Error] Output folder check failed." + Style.RESET_ALL)
            return None

    # Get velocity layers list from the preprocessed image
    try:
        layer_model = dependencies.get_layer_model(preprocessed_img)
    except Exception as e:
        print(Fore.RED + f"[Error] Unexpected error: {e}" + Style.RESET_ALL)
        print(Fore.RED + f"[Error] Getting layer model for radar denoise process failed." + Style.RESET_ALL)
        return None


    # Get denoise image
    try:
        neg_denoise_img = layer_analysis.get_denoise_img(preprocessed_img, layer_model,
                                                         "neg", enable_debug, debug_output_path)
        pos_denoise_img = layer_analysis.get_denoise_img(preprocessed_img, layer_model,
                                                         "pos", enable_debug, debug_output_path)
    except Exception as e:
        print(Fore.RED + f"[Error] Unexpected error: {e}" + Style.RESET_ALL)
        print(Fore.RED + f"[Error] layer analysis processing failed." + Style.RESET_ALL)
        return None

    # Integrate two denoised image
    try:
        integrate_img = velocity_integrate.integrate_velocity_mode(neg_denoise_img, pos_denoise_img,
                                                                   enable_debug, debug_output_path)
    except Exception as e:
        print(Fore.RED + f"[Error] Unexpected error: {e}" + Style.RESET_ALL)
        print(Fore.RED + f"[Error] Velocity integration processing failed." + Style.RESET_ALL)
        return None

    # Velocity unfolding
    try:
        unfold_img = velocity_unfold.unfold_echoes(integrate_img, enable_debug, debug_output_path)
    except Exception as e:
        print(Fore.RED + f"[Error] Unexpected error: {e}" + Style.RESET_ALL)
        print(Fore.RED + f"[Error] Velocity unfolding failed." + Style.RESET_ALL)
        return None

    end = time.time()
    duration = end - start
    print(f"[Info] Duration of radar denoise process: {duration:.4f} seconds.")
    return unfold_img

