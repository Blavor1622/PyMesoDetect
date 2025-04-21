from PIL import Image, ImageDraw
import os
import utils
from utils import gray_value_interval
import math
import time

analysis_result_folder = "meso_analysis/"
analysis_debug_folder = "debug/"

CENTER_DIAMETER = 4
CENTER_DISTANCE_THRESHOLD = 24 # (183 - 65) pixels/ 50 km = 2.36 pixel per kilometer


def meso_detect(folder_path, unfold_img_path, neg_peaks, pos_peaks):
    start = time.time()
    print("[Info] Start mesocyclone detection...")
    # Check folder path
    analysis_result_folder_path = folder_path + analysis_result_folder
    if not os.path.exists(analysis_result_folder_path):
        os.makedirs(analysis_result_folder_path)
    analysis_debug_folder_path = analysis_result_folder_path + analysis_debug_folder
    if not os.path.exists(analysis_debug_folder_path):
        os.makedirs(analysis_debug_folder_path)

    # Load unfold image
    unfold_img = Image.open(unfold_img_path)

    # Get group centers
    neg_centers = []
    for group in neg_peaks:
        center = get_group_center(unfold_img, group)
        neg_centers.append(center)
    pos_centers = []
    for group in pos_peaks:
        center = get_group_center(unfold_img, group)
        pos_centers.append(center)

    meso_pairs = []
    for neg_center in neg_centers:
        for pos_center in pos_centers:
            # Calculate distance
            center_distance = math.sqrt((neg_center[0] - pos_center[0]) ** 2 + (neg_center[1] - pos_center[1]) ** 2)
            if center_distance <= CENTER_DISTANCE_THRESHOLD:
                meso_pairs.append((neg_center, pos_center, center_distance))

    # Meso detection debug image
    meso_debug_img = Image.new("RGB", unfold_img.size, (0, 0, 0))
    meso_debug_draw = ImageDraw.Draw(meso_debug_img)
    # Debug meso detect result
    for meso_pair in meso_pairs:
        # Draw center area with fixed diameter
        neg_center = meso_pair[0]
        for x in range(neg_center[0] - CENTER_DIAMETER, neg_center[0] + CENTER_DIAMETER + 1):
            for y in range(neg_center[1] - CENTER_DIAMETER, neg_center[1] + CENTER_DIAMETER + 1):
                if math.sqrt((x - neg_center[0]) ** 2 + (y - neg_center[1]) ** 2) <= CENTER_DIAMETER:
                    meso_debug_draw.point((x, y), (0, 0, 255))
        meso_debug_draw.point(neg_center, (0, 255, 0))

        pos_center = meso_pair[1]
        for x in range(pos_center[0] - CENTER_DIAMETER, pos_center[0] + CENTER_DIAMETER + 1):
            for y in range(pos_center[1] - CENTER_DIAMETER, pos_center[1] + CENTER_DIAMETER + 1):
                if math.sqrt((x - pos_center[0]) ** 2 + (y - pos_center[1]) ** 2) <= CENTER_DIAMETER:
                    meso_debug_draw.point((x, y), (255, 0, 0))
        meso_debug_draw.point(pos_center, (0, 255, 0))

        meso_debug_draw.line([neg_center, pos_center], fill=(0, 255, 255), width=1)

    # Save debug result image
    meso_debug_img.save(analysis_debug_folder_path + "meso_detect.png")

    # Generate a detection result image
    cv_pairs = utils.get_color_bar_info("color_velocity_pairs")
    meso_result_img = Image.new("RGB", unfold_img.size, (0, 0, 0))
    meso_result_draw = ImageDraw.Draw(meso_result_img)
    for meso_pair in meso_pairs:
        neg_center = meso_pair[0]
        pos_center = meso_pair[1]
        range_diameter = round(meso_pair[2])
        # Calculate mid-center of the meso pair
        mid_center_x = round((neg_center[0] + pos_center[0]) / 2)
        mid_center_y = round((neg_center[1] + pos_center[1]) / 2)
        # Draw detect area
        for x in range(mid_center_x - range_diameter, mid_center_x + range_diameter + 1):
            for y in range(mid_center_y - range_diameter, mid_center_y + range_diameter + 1):
                if math.sqrt((x - mid_center_x) ** 2 + (y - mid_center_y) ** 2) <= range_diameter:
                    # Extract echo value
                    echo_value = unfold_img.getpixel((x, y))
                    echo_index = round(echo_value[0] / gray_value_interval) - 1
                    if echo_index not in range(len(cv_pairs)):
                        continue
                    meso_result_draw.point((x, y), cv_pairs[echo_index][0])
        # Save result image
        meso_result_img.save(analysis_result_folder_path + "meso_detect.png")
    end = time.time()
    duration = end - start
    print(f"[Info] Duration of mesocyclone detection: {duration:.4f} seconds")
    return meso_result_img


def get_group_center(refer_img, echo_group):
    # Get basic data
    cv_pairs = utils.get_color_bar_info("color_velocity_pairs")
    # Iterate through group
    center_x_sum = 0
    center_y_sum = 0
    weight_sum = 0
    for echo_coord in echo_group:
        echo_value = refer_img.getpixel(echo_coord)
        echo_index = round(echo_value[0] / gray_value_interval) - 1

        weight = abs(cv_pairs[echo_index][1])
        center_x_sum += echo_coord[0] * weight
        center_y_sum += echo_coord[1] * weight
        weight_sum += weight
    # Calculate center coord
    if weight_sum == 0:
        return
    center_x = round(center_x_sum / weight_sum)
    center_y = round(center_y_sum / weight_sum)
    center = (center_x, center_y)
    return center
