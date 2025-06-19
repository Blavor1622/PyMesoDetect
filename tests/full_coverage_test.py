from MesoDetect import meso_detect
from pathlib import Path
from MesoDetect.DataIO.folder_utils import get_folder_image_paths

VALID_IMG_EXTENSION = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}



if __name__ == "__main__":
    # Get the project root (where this script lives)
    PROJECT_ROOT = Path(__file__).parent.parent  # Adjust .parent count based on your file's depth
    test_img_folder_path = r"C:\Users\Blavor\Desktop\中气旋数据集\2025\4.22四会中气旋\Z9200\vel"

    img_paths = get_folder_image_paths(test_img_folder_path)
    for image_path in img_paths:
        output_folder_path = str(PROJECT_ROOT / "data/result/single/test2")
        meso_detect.meso_detect(image_path, output_folder_path)
