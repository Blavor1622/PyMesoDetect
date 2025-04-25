from PIL import Image
import os
import time
from Preprocess.RadarDenoise import dependencies
from Preprocess.RadarDenoise import layer_analysis
from Preprocess.RadarDenoise import velocity_unfold
from Preprocess.RadarDenoise import velocity_integrate


analysis_folder = "layer_denoise/"
debug_folder = "layer_debug/"
"""
    layer denoise interface
"""
def radar_denoise(folder_path, narrow_filled_path):
    """
    Apply velocity layer analysis to denoise and velocity unfolding
    Args:
        folder_path: path of result images folder
        narrow_filled_path: path of narrow filled gray image

    Returns: path of analysis result image with string format

    """
    start = time.time()
    print("[Info] Start layer filling analysis...")
    # Check result folder
    analysis_result_folder = folder_path + analysis_folder
    if not os.path.exists(analysis_result_folder):
        os.makedirs(analysis_result_folder)
    analysis_debug_folder = analysis_result_folder + debug_folder
    if not os.path.exists(analysis_debug_folder):
        os.makedirs(analysis_debug_folder)

    # Load images
    fill_img = Image.open(narrow_filled_path)
    # Get velocity layers list from the fill image
    layer_model = dependencies.get_layer_model(fill_img)

    # Get denoise image
    neg_denoise_img = layer_analysis.get_denoise_img(fill_img, layer_model, "neg", analysis_debug_folder)
    pos_denoise_img = layer_analysis.get_denoise_img(fill_img, layer_model, "pos", analysis_debug_folder)

    # Save denoise image
    neg_denoise_img_path = analysis_result_folder + "neg_denoised.png"
    pos_denoise_img_path = analysis_result_folder + "pos_denoised.png"
    neg_denoise_img.save(neg_denoise_img_path)
    pos_denoise_img.save(pos_denoise_img_path)

    # Integrate two denoised image
    integrate_img = velocity_integrate.integrate_velocity_mode(neg_denoise_img, pos_denoise_img, analysis_debug_folder)

    # Save integrated image
    integrate_img_path = analysis_result_folder + "denoised_integrate.png"
    integrate_img.save(integrate_img_path)

    # Velocity unfolding
    unfold_img = velocity_unfold.unfold_echoes(integrate_img, analysis_debug_folder)

    # Save unfolded image
    unfold_img_path = analysis_result_folder + "unfold.png"
    unfold_img.save(unfold_img_path)

    end = time.time()
    duration = end - start
    print(f"[Info] Duration of layer filling analysis: {duration:.4f} seconds.")
    return neg_denoise_img_path, pos_denoise_img_path, integrate_img_path, unfold_img_path

