from MesoDetect import meso_detect
from pathlib import Path
import os
VALID_IMG_EXTENSION = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}



if __name__ == "__main__":
    # Get the project root (where this script lives)
    PROJECT_ROOT = Path(__file__).parent.parent  # Adjust .parent count based on your file's depth
    test_img_folder_path = ""

    # Get image names from input folder
    all_files = os.listdir(test_img_folder_path)
    image_files = [file for file in all_files if os.path.splitext(file)[1].lower() in VALID_IMG_EXTENSION]

    for image_name in image_files:
        image_path = test_img_folder_path + image_name
        output_folder_path = str(PROJECT_ROOT / "data/result/single/fct_nf") + "/" + image_name.split(".")[0] + "/"
        meso_detect.meso_detect(image_path, output_folder_path, "", enable_debug_mode=True)
