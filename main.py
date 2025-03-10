import basis
import os
import utils
from Preprocess import read_radar
from Preprocess import fill_blank
from Preprocess import blur
from SinkSimulation import gray

if __name__ == '__main__':
    # Set radar images folder
    img_folder = "D:/radar_sources/"
    results_folder = 'D:/analysis_result/'

    # Generate image config
    basis.check_input_folder(img_folder)
    # Check config file
    basis.validate_config()

    # Get image names from input folder
    all_files = os.listdir(img_folder)
    image_files = [file for file in all_files if os.path.splitext(file)[1].lower() in utils.valid_image_extensions]

    # Analise each radar image
    for image_name in image_files:
        # Generate image entire path and result folder path
        image_path = img_folder + image_name
        result_folder_path = results_folder + image_name.split(".")[0]

        print(f"image_path = {image_path}")
        print(f"result_folder_path = {result_folder_path}")

        rlt_path = read_radar.process_rlt_saving(result_folder_path, image_path)

        filled_path = fill_blank.process_rlt_saving(result_folder_path, rlt_path)

        blur.remove_velocity_blur(result_folder_path, filled_path)

        gray.get_gray_img(result_folder_path, "neg")
