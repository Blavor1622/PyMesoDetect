import basis
import os
import utils
import time
from Preprocess import read_data
from Preprocess import fill_blank
from Preprocess import cover_boundary
from Preprocess.RadarDenoise import denoise
from ImmerseSimulation import peak_analysis
from MesoDetection import meso_analysis


if __name__ == '__main__':
    # Set radar images folder
    img_folder = "C:/Users/12103/Desktop/4.22四会中气旋/"
    station_num = "Z9200"
    results_folder = "results/analysis_result/Z9200/"
    detect_result_folder = "results/detect_result/Z9200/"

    # Generate image config
    basis.check_input_folder(img_folder)
    # Check config file
    basis.validate_config()

    # Get image names from input folder
    all_files = os.listdir(img_folder)
    image_files = [file for file in all_files if os.path.splitext(file)[1].lower() in utils.valid_image_extensions]

    # Check station
    if station_num in utils.need_cover_station:
        need_cover = True
        print("[Info] This radar images need to cover boundaries.")
    else:
        need_cover = False

    # Check result folder
    if not os.path.exists(detect_result_folder):
        os.makedirs(detect_result_folder)

    # Analise each radar image
    for image_name in image_files:
        start = time.time()
        # Generate image entire path and result folder path
        image_path = img_folder + image_name
        result_folder_path = results_folder + image_name.split(".")[0] + '/'
        print("----------------------------------")
        print(f"image_path = {image_path}")
        print(f"result_folder_path = {result_folder_path}")

        # Check whether to cover the boundary or not
        if need_cover:
            image_path = cover_boundary.cover_white_boundary(image_path, station_num, result_folder_path)

        gray_img_path = read_data.read_radar_image(result_folder_path, image_path)

        utils.visualize_result(result_folder_path, gray_img_path, "read_result")

        filled_img_path = fill_blank.fill_radar_image(result_folder_path, gray_img_path)

        utils.visualize_result(result_folder_path, filled_img_path, "filled")

        neg_denoise_img_path, pos_denoise_img_path, integrate_img_path, unfold_img_path\
            = denoise.radar_denoise(result_folder_path, filled_img_path)

        utils.visualize_result(result_folder_path, neg_denoise_img_path, "neg_denoise")

        utils.visualize_result(result_folder_path, pos_denoise_img_path, "pos_denoise")

        utils.visualize_result(result_folder_path, integrate_img_path, "integrate")

        utils.visualize_result(result_folder_path, unfold_img_path, "unfold")

        utils.velocity_mode_division(result_folder_path, filled_img_path)

        neg_peaks, pos_peaks = peak_analysis.immerse_analysis(result_folder_path, unfold_img_path)

        meso_detect_result_img = meso_analysis.meso_detect(result_folder_path, unfold_img_path, neg_peaks, pos_peaks)

        meso_detect_result_img.save(detect_result_folder + "DMD_" + image_name.split(".")[0] + ".png")

        end = time.time()
        duration = end - start
        print(f"[Info] Final duration of execution: {duration:.4f} seconds")