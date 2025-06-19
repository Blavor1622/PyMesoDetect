"""
this file mainly provides public utility functions about folder process
"""
import os
from colorama import Fore, Style
from PIL import Image
from typing import Union, Optional, List
from pathlib import Path
from MesoDetect.DataIO.consts import VALID_IMG_EXTENSION


def check_output_folder(output_folder_path: Union[str, Path], current_folder_name: str) -> Optional[Path]:
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


def save_output_image(output_image_folder: str, input_image_path: str, output_image: Image, image_name: str):
    result_img_folder = output_image_folder + input_image_path.split("/")[-1].split(".")[0] + "/"
    if not os.path.exists(result_img_folder):
        os.makedirs(result_img_folder)
    output_image_path = result_img_folder + image_name
    output_image.save(output_image_path)


def get_folder_image_paths(img_folder_path: Union[Path, str]) -> List[Path]:
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