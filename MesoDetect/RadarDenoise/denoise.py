from PIL import Image
import time
from colorama import Fore, Style
from MesoDetect.RadarDenoise import layer_analysis, dependencies, velocity_integrate, velocity_unfold
from MesoDetect.DataIO.folder_utils import check_output_folder
from MesoDetect.RadarDenoise.consts import CURRENT_DEBUG_RESULT_FOLDER


"""
    layer denoise interface
"""
def radar_denoise(
        preprocessed_img: Image,
        enable_debug: bool = False,
        debug_output_path: str = ""
):
    """
    Apply velocity layer analysis to denoise and velocity unfolding
    Args:
        preprocessed_img: preprocessed radar image in internal gray format
        enable_debug: boolean flag enabling debug mode for saving analysis result image
        debug_output_path: output location path for analysis result image saving

    Returns: denoised image in PIL.Image type, None otherwise

    """

    start = time.time()
    print("[Info] Start radar denoise process...")
    if enable_debug:
        if debug_output_path == "":
            print(Fore.RED + f"[Error] Conflict parameters value: enable_debug: {enable_debug} "
                             f"while debug_output_path: {debug_output_path}." + Style.RESET_ALL)
            return None
        debug_output_path = check_output_folder(debug_output_path, CURRENT_DEBUG_RESULT_FOLDER)
        if debug_output_path is None:
            print(Fore.RED + "[Error] Radar denoise process fail." + Style.RESET_ALL)
            return None

    # Get velocity layers list from the preprocessed image
    layer_model = dependencies.get_layer_model(preprocessed_img)

    # Get denoise image
    neg_denoise_img = layer_analysis.get_denoise_img(preprocessed_img, layer_model, "neg", enable_debug, debug_output_path)
    pos_denoise_img = layer_analysis.get_denoise_img(preprocessed_img, layer_model, "pos", enable_debug, debug_output_path)

    # Integrate two denoised image
    integrate_img = velocity_integrate.integrate_velocity_mode(neg_denoise_img, pos_denoise_img, enable_debug, debug_output_path)

    # Velocity unfolding
    unfold_img = velocity_unfold.unfold_echoes(integrate_img, enable_debug, debug_output_path)

    end = time.time()
    duration = end - start
    print(f"[Info] Duration of radar denoise process: {duration:.4f} seconds.")
    return neg_denoise_img, pos_denoise_img, integrate_img, unfold_img

