from PIL import Image, ImageDraw
import os
from MesoDetect.DataIO.consts import GRAY_SCALE_UNIT
from MesoDetect.DataIO import radar_config


def visualize_result(folder_path, gray_img, result_name):
    """
    Turning gray image into original radar image for visualization the preprocess result.
    :param folder_path: path of result folder
    :param gray_img: PIL Image object of gray image
    :param result_name: name of visualized result image
    :return: path of visualization result image
    """
    # Check result path
    visualize_result_path = folder_path + "visualization/"
    if not os.path.exists(visualize_result_path):
        os.makedirs(visualize_result_path)

    # Create visualization result image
    visual_img = Image.new("RGB", gray_img.size, (0, 0, 0))
    visual_draw = ImageDraw.Draw(visual_img)

    # Iterate gray image
    radar_zone = radar_config.get_radar_info("radar_zone")
    cv_pairs = radar_config.get_color_bar_info("color_velocity_pairs")
    for x in range(radar_zone[0], radar_zone[1]):
        for y in range(radar_zone[0], radar_zone[1]):
            # Get current pixel value
            pixel_value = gray_img.getpixel((x, y))[0]
            # Calculate gray value index
            gray_value_index = round(1.0 * pixel_value / GRAY_SCALE_UNIT) - 1
            # Get actual color and draw
            if 0 <= gray_value_index <= len(cv_pairs) - 1:
                visual_draw.point((x, y), cv_pairs[gray_value_index][0])

    # Save visualization result image
    visualization_result_path = visualize_result_path + result_name + ".png"
    visual_img.save(visualization_result_path)

    return visualization_result_path


def velocity_mode_division(folder_path, gray_img_path):
    # Check result path
    visualize_result_path = folder_path + "visualization/"
    if not os.path.exists(visualize_result_path):
        os.makedirs(visualize_result_path)
    # Load filled image
    fill_img = Image.open(gray_img_path)
    # Create result images
    neg_img = Image.new("RGB", fill_img.size, (0, 0, 0))
    pos_img = Image.new("RGB", fill_img.size, (0, 0, 0))
    neg_draw = ImageDraw.Draw(neg_img)
    pos_draw = ImageDraw.Draw(pos_img)
    # Get basic data
    radar_zone = radar_config.get_radar_info("radar_zone")
    cv_pairs = radar_config.get_color_bar_info("color_velocity_pairs")
    base_index = round(len(cv_pairs) / 2) - 1
    for x in range(radar_zone[0], radar_zone[1]):
        for y in range(radar_zone[0], radar_zone[1]):
            pixel_value = fill_img.getpixel((x, y))[0]
            pixel_index = round(1.0 * pixel_value / GRAY_SCALE_UNIT) - 1
            if pixel_index >= 0:
                if pixel_index <= base_index:
                    neg_draw.point((x, y), cv_pairs[pixel_index][0])
                else:
                    pos_draw.point((x, y), cv_pairs[pixel_index][0])
    # Save result images
    neg_img.save(visualize_result_path + "neg_filled.png")
    pos_img.save(visualize_result_path + "pos_filled.png")
