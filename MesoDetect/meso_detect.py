import os
import time
from MesoDetect.DataIO import radar_config
from MesoDetect.DataIO.preprocessor import get_gray_img


def meso_detect(img_path: str, station_num: str, output_folder_path: str, enable_default_config: bool = True, enable_debug_mode: bool = False):
    start = time.time()
    print("----------------------------------")
    print(f"image_path = {img_path}")

    if enable_debug_mode:
        # Extract image name
        img_name = img_path.split("/")[-1].split(".")[0]
        print(f"[Debug] Img name: {img_name}")
        # Get result folder path
        debug_images_folder_path = output_folder_path + img_name + "/"
        if not os.path.exists(debug_images_folder_path):
            os.makedirs(debug_images_folder_path)
    else:
        # Empty path indicate that debug mode is disabled
        debug_images_folder_path = ""
    print(f"result_folder_path = {debug_images_folder_path}")

    # Setup radar image config
    radar_config.setup_radar_img_config(img_path, False, enable_default_config)

    # Get gray image
    gray_img = get_gray_img(img_path, station_num, enable_debug_mode, debug_images_folder_path)

    end = time.time()
    duration = end - start
    print(f"[Info] Final duration of execution: {duration:.4f} seconds")
