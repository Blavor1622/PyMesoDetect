"""
this file mainly provides public utility functions about folder process
"""
import os
from colorama import Fore, Style
from PIL import Image


def check_output_folder(output_folder_path: str, current_folder_name: str):
    try:
        current_folder_path = output_folder_path + current_folder_name
        if not os.path.exists(current_folder_path):
            os.makedirs(current_folder_path)
    except Exception as e:
        print(Fore.RED + f"[Error] Unexpected error: {e}" + Style.RESET_ALL)
        return None
    return current_folder_path


def save_output_image(output_image_folder: str, input_image_path: str, output_image: Image, image_name: str):
    result_img_folder = output_image_folder + input_image_path.split("/")[-1].split(".")[0] + "/"
    if not os.path.exists(result_img_folder):
        os.makedirs(result_img_folder)
    output_image_path = result_img_folder + image_name
    output_image.save(output_image_path)
