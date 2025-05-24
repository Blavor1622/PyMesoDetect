from MesoDetect import meso_detect
from pathlib import Path


if __name__ == "__main__":
    # Get the project root (where this script lives)
    PROJECT_ROOT = Path(__file__).parent.parent  # Adjust .parent count based on your file's depth

    image_path = ""

    output_folder_path = str(PROJECT_ROOT / "data/result/single/test1") + "/"

    meso_detect.meso_detect(image_path, output_folder_path, "")
