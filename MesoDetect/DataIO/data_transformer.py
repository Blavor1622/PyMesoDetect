from PIL import Image, ImageDraw
import os
from MesoDetect.DataIO.consts import GRAY_SCALE_UNIT
from MesoDetect.DataIO import radar_config
from MesoDetect.MesocycloneAnalysis.consts import MesocycloneInfo
from MesoDetect.DataIO.consts import DetectionResult
import math
from pathlib import Path
from typing import List


def visualize_result(folder_path: Path, gray_img: Image, result_name: str) -> str:
    """
    Turning gray image into original radar image for visualization the preprocess result.
    :param folder_path: path of result folder
    :param gray_img: PIL Image object of gray image
    :param result_name: name of visualized result image
    :return: path of visualization result image
    """
    # Check result path
    visualize_result_path = folder_path / "visualization"
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
    visualization_result_path = visualize_result_path / (result_name + ".png")
    visual_img.save(visualization_result_path)

    return visualization_result_path.as_posix()


def pack_detection_result(
        station_number: str,
        resolved_img_path: Path,
        refer_img: Image,
        meso_list: List[MesocycloneInfo],
        output_path: Path
) -> DetectionResult:
    """
    Pack mesocyclone list from mesocyclone analysis and generate detection result visualization images.
    Args:
        station_number: radar station number
        resolved_img_path: resolved origial radar image path
        refer_img: reference image for echo color value
        meso_list: list of mesocyclone info dictionary data
        output_path: path for generating result visualiztion images

    Returns:
        packed detection result data
    """
    # Get scan time from resolved image path
    scan_time = resolved_img_path.as_posix().split("/")[-1].split("_")[4]

    # Get basic data
    cv_pairs = radar_config.get_color_bar_info("color_velocity_pairs")
    image_size = radar_config.get_radar_info("image_size")

    # Iterate meso list for generating result images
    result_image_paths: List[str] = []
    for idx, meso_info in enumerate(meso_list, start=1):
        meso_result_img = Image.new("RGB", image_size, (0, 0, 0))
        meso_result_draw = ImageDraw.Draw(meso_result_img)
        neg_center = meso_info['neg_center']
        pos_center = meso_info['pos_center']
        range_diameter = round(math.sqrt((neg_center[0] - pos_center[0]) ** 2 + (neg_center[1] - pos_center[1]) ** 2))
        # Calculate mid-center of the meso pair
        mid_center_x = round((neg_center[0] + pos_center[0]) / 2)
        mid_center_y = round((neg_center[1] + pos_center[1]) / 2)
        # Draw detect area
        for x in range(mid_center_x - range_diameter, mid_center_x + range_diameter + 1):
            for y in range(mid_center_y - range_diameter, mid_center_y + range_diameter + 1):
                if math.sqrt((x - mid_center_x) ** 2 + (y - mid_center_y) ** 2) <= range_diameter:
                    # Extract echo value
                    echo_value = refer_img.getpixel((x, y))
                    echo_index = round(echo_value[0] / GRAY_SCALE_UNIT) - 1
                    if echo_index not in range(len(cv_pairs)):
                        continue
                    meso_result_draw.point((x, y), cv_pairs[echo_index][0])
        result_image_path = output_path / ("meso_detect" + str(idx) + ".png")
        meso_result_img.save(result_image_path)
        result_image_paths.append(result_image_path.as_posix())

    detection_result: DetectionResult = {
        "station_number": station_number,
        "scan_time": scan_time,
        "meso_list": meso_list,
        "result_img_paths": result_image_paths
    }

    return detection_result


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
