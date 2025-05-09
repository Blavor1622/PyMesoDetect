from PIL import Image, ImageDraw
import os
from MesoDetect.ReadData import utils
from MesoDetect.ReadData.utils import gray_value_interval
import math
import time

analysis_result_folder = "meso_analysis/"
analysis_debug_folder = "debug/"

CENTER_DIAMETER = 4
CENTER_DISTANCE_THRESHOLD = 24 # (183 - 65) pixels/ 50 km = 2.36 pixel per kilometer
MESO_ROTATION_THRESHOLD = 9.5 # m/s, threshold for the rotation speed of meso
VALID_MESO_ECHO_RATIO_THRESHOLD = 0.89 # threshold for checking invalid echo ratio in the meso range

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

    # Meso Data Structure containing neg, pos center coordinate and float type center distance
    meso_pairs = []
    cv_pairs = utils.get_color_bar_info("color_velocity_pairs")
    for neg_idx in range(len(neg_centers)):
        for pos_idx in range(len(pos_centers)):
            neg_center = neg_centers[neg_idx]
            pos_center = pos_centers[pos_idx]
            center_distance = math.sqrt((neg_center[0] - pos_center[0]) ** 2 + (neg_center[1] - pos_center[1]) ** 2)
            if center_distance <= CENTER_DISTANCE_THRESHOLD:
                # Iterate through each peak and get maximum velocity value
                maximum_neg_velocity = 0
                for coord in neg_peaks[neg_idx]:
                    neg_peak_echo_value = unfold_img.getpixel(coord)
                    neg_peak_echo_index = round(neg_peak_echo_value[0] / gray_value_interval) - 1
                    if neg_peak_echo_index in range(len(cv_pairs)):
                        neg_peak_echo_velocity = cv_pairs[neg_peak_echo_index][1]
                    else:
                        continue
                    if neg_peak_echo_velocity < maximum_neg_velocity:
                        maximum_neg_velocity = neg_peak_echo_velocity
                maximum_pos_velocity = 0
                for coord in pos_peaks[pos_idx]:
                    pos_peak_echo_value = unfold_img.getpixel(coord)
                    pos_peak_echo_index = round(pos_peak_echo_value[0] / gray_value_interval) - 1
                    if pos_peak_echo_index in range(len(cv_pairs)):
                        pos_peak_echo_velocity = cv_pairs[pos_peak_echo_index][1]
                    else:
                        continue
                    if pos_peak_echo_velocity > maximum_pos_velocity:
                        maximum_pos_velocity = pos_peak_echo_velocity
                avg_rotation = (abs(maximum_neg_velocity) + abs(maximum_pos_velocity)) / 2
                if avg_rotation >= MESO_ROTATION_THRESHOLD:
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

    # Filter out fake meso
    meso_pairs = filter_fake_meso(unfold_img, meso_pairs)

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


def filter_fake_meso(unfold_img, meso_pairs):
    filtered_meso_pairs = []
    for meso_pair in meso_pairs:
        # Get meso center
        neg_center = meso_pair[0]
        pos_center = meso_pair[1]
        mid_center_x = round((neg_center[0] + pos_center[0]) / 2)
        mid_center_y = round((neg_center[1] + pos_center[1]) / 2)
        # Get meso diameter
        range_radius = round(meso_pair[2])
        # Iterate meso range to calculate empty and basemaps echo ratio
        # Note that the valid echoes do not include basemaps filled echoes
        invalid_echo_num = 0
        total_in_range_pixel_num = 0
        for x in range(mid_center_x - range_radius, mid_center_x + range_radius):
            for y in range(mid_center_y - range_radius, mid_center_y + range_radius):
                if not math.sqrt((x - mid_center_x) ** 2 + (y - mid_center_y) ** 2) <= range_radius:
                    # Skip coordinate that out of range
                    continue
                total_in_range_pixel_num += 1
                # Get pixel value
                pixel_value = unfold_img.getpixel((x, y))
                # Calculate gray value index, use second channel RGB value
                pixel_value_index = round(pixel_value[1] / gray_value_interval) - 1
                if pixel_value_index == -1:
                    invalid_echo_num += 1
        if total_in_range_pixel_num > 0:
            invalid_echo_ratio = invalid_echo_num / total_in_range_pixel_num
        else:
            invalid_echo_ratio = 1
        # Check with threshold
        if invalid_echo_ratio <= 1 - VALID_MESO_ECHO_RATIO_THRESHOLD:
            filtered_meso_pairs.append(meso_pair)
    return filtered_meso_pairs




