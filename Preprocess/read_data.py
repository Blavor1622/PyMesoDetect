from PIL import Image, ImageDraw
import utils
import os
import time

read_result_folder = 'read_result/'
gray_image_name = 'radar_gray.png'


def read_radar_image(folder_path, radar_img_path):
    """
    Generating a gray image from the original radar image
    so that later process can base on this gray image
    :param folder_path: path of current result folder
    :param radar_img_path: path of original radar image
    :return: path of gray image if generation is success
    """
    start = time.time()
    print("[Info] Start processing radar data...")
    # Check result path
    if not os.path.exists(folder_path + read_result_folder):
        os.makedirs(folder_path + read_result_folder)

    # Open radar image
    radar_img = Image.open(radar_img_path)

    # Result images
    gray_img = Image.new("RGB", radar_img.size, (0, 0, 0))
    gray_draw = ImageDraw.Draw(gray_img)

    # Iterate the radar zone to read echo data
    radar_zone = utils.get_radar_info("radar_zone")
    cv_pairs = utils.get_color_bar_info("color_velocity_pairs")
    for x in range(radar_zone[0], radar_zone[1]):
        for y in range(radar_zone[0], radar_zone[1]):
            # Get current pixel value
            pixel_value = radar_img.getpixel((x, y))

            # Match echo color
            for idx in range(len(cv_pairs)):
                if all(abs(c1 - c2) <= 10 for c1, c2 in zip(pixel_value[:3], cv_pairs[idx][0][:3])):
                    gray_value = (idx + 1) * utils.gray_value_interval
                    gray_draw.point((x, y), (gray_value, gray_value, gray_value))

    # Save result image
    gray_img_path = folder_path + read_result_folder + gray_image_name
    gray_img.save(gray_img_path)

    end = time.time()
    duration = end - start
    print(f'[Info] duration of radar reading: {duration:.4f} seconds')
    return gray_img_path

