from MesoDetect import meso_detect
from pathlib import Path


if __name__ == "__main__":
    # Get the project root (where this script lives)
    PROJECT_ROOT = Path(__file__).parent.parent  # Adjust .parent count based on your file's depth
    # image_path = "C:/Users/Blavor/Desktop/中气旋数据集/2024/4.21潮揭中气旋/Z9754/vel/Z_RADR_I_Z9754_202404210624_P_DOR_SA_V_5_115_15.754.png"
    image_path = "C:/Users/Blavor/Desktop/中气旋数据集/2024/4.30珠海超单/Z9755/vel/Z_RADR_I_Z9755_202404301154_P_DOR_SAD_V_5_115_15.755.png.png"
    output_folder_path = str(PROJECT_ROOT / "data/result/single/test2") + "/"
    station_num = "Z9755"
    meso_detect.meso_detect(image_path, station_num, output_folder_path, enable_debug_mode=True)
