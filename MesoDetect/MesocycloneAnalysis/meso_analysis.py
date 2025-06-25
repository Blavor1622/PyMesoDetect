import math
import time
from MesoDetect.DataIO.utils import get_color_bar_info, get_radar_info
from MesoDetect.DataIO.consts import GRAY_SCALE_UNIT
from typing import List, Tuple, Optional
from pathlib import Path
from MesoDetect.DataIO.utils import check_output_folder
from colorama import Fore, Style
from PIL import Image, ImageDraw
from MesoDetect.ImmerseSimulation.peak_detector import draw_extrema_regions
from MesoDetect.MesocycloneAnalysis.consts import (MesocycloneInfo, CURRENT_DEBUG_RESULT_FOLDER,
                                                   CENTER_DISTANCE_THRESHOLD, MESO_ROTATION_THRESHOLD,
                                                   VALID_MESO_ECHO_RATIO_THRESHOLD, CENTER_DIAMETER)

"""
    Interface for meso analysis
"""
def opposite_extrema_analysis(
        unfold_img: Image,
        neg_peaks: List[List[Tuple[int, int]]],
        pos_peaks: List[List[Tuple[int, int]]],
        output_path: Path,
        enable_debug: bool = False
) -> Optional[List[MesocycloneInfo]]:
    """
    Detect mesocyclones from given negative and positive velocity echo extrema regions.
    Args:
        unfold_img: unfold radar image in gray mode
        neg_peaks: negative velocity echo extrema regions
        pos_peaks: positive velocity echo extrema retions
        output_path: path of output images
        enable_debug: bool flag for debug mode

    Returns:
        a list of mesocyclone data structure
    """
    start = time.time()
    print("[Info] Start mesocyclone analysis...")
    debug_output_path = output_path
    if enable_debug:
        debug_output_path = check_output_folder(output_path, CURRENT_DEBUG_RESULT_FOLDER)
        if debug_output_path is None:
            print(Fore.RED + "[Error] Output folder check failed." + Style.RESET_ALL)
            return None

    try:
        # check meso conditions for each opposite extrema pair
        mesocyclone_list = validate_potential_meso(unfold_img, neg_peaks, pos_peaks)
    except Exception as e:
        print(Fore.RED + f"[Error] Unexpected error: {e}" + Style.RESET_ALL)
        print(Fore.RED + f"[Error] Validing potential mesocyclone process failed." + Style.RESET_ALL)
        return None

    # draw mesocyclone analysis debug image
    if enable_debug:
        try:
            get_meso_debug_img(neg_peaks, pos_peaks, mesocyclone_list, unfold_img, "meso_analysis_debug", debug_output_path)
        except Exception as e:
            print(Fore.RED + f"[Error] Unexpected error: {e}" + Style.RESET_ALL)
            print(Fore.RED + f"[Error] Generating debug image for mesocyclone analysis failed." + Style.RESET_ALL)
            return None
    end = time.time()
    duration = end - start
    print(f"[Info] Duration of mesocyclone analysis: {duration:.4f} seconds")

    print("------Detection Result------")
    for idx, mesocyclone_dict in enumerate(mesocyclone_list, start=1):
        print(f"\nMesocyclone #{idx}:")
        print(f"    logic_center: {mesocyclone_dict['logic_center']}")
        print(f"    radar_distance: {mesocyclone_dict['radar_distance']}")
        print(f"    radar_angle: {mesocyclone_dict['radar_angle']}")
        print(f"    shear_value: {mesocyclone_dict['shear_value']}")
        print(f"    neg_center: {mesocyclone_dict['neg_center']}")
        print(f"    neg_max_velocity: {mesocyclone_dict['neg_max_velocity']}")
        print(f"    pos_center: {mesocyclone_dict['pos_center']}")
        print(f"    pos_max_velocity: {mesocyclone_dict['pos_max_velocity']}")

    return mesocyclone_list


"""
    dependency functions
"""
def validate_potential_meso(
        unfold_img: Image,
        neg_peaks: List[List[Tuple[int, int]]],
        pos_peaks: List[List[Tuple[int, int]]],
) -> Optional[List[MesocycloneInfo]]:
    # Get group centers
    neg_centers = []
    for group in neg_peaks:
        center = get_group_center(unfold_img, group)
        if not center is None:
            neg_centers.append(center)
    pos_centers = []
    for group in pos_peaks:
        center = get_group_center(unfold_img, group)
        if not center is None:
            pos_centers.append(center)

    # Meso Data Structure containing neg, pos center coordinate and float type center distance
    mesocyclone_list: List[MesocycloneInfo] = []
    cv_pairs = get_color_bar_info("color_velocity_pairs")
    radar_center = get_radar_info("radar_center")
    for neg_idx in range(len(neg_centers)):
        for pos_idx in range(len(pos_centers)):
            # Get extrema region center coordinate
            neg_center = neg_centers[neg_idx]
            pos_center = pos_centers[pos_idx]
            # Calculate center distance
            center_distance = math.sqrt((neg_center[0] - pos_center[0]) ** 2 + (neg_center[1] - pos_center[1]) ** 2)
            # Check opposite extrema region center distance
            if center_distance <= CENTER_DISTANCE_THRESHOLD:
                # Get maxinum velocity value from extrema region
                # For negative:
                maximum_neg_velocity = 0
                for coord in neg_peaks[neg_idx]:
                    neg_peak_echo_value = unfold_img.getpixel(coord)
                    neg_peak_echo_index = round(neg_peak_echo_value[0] / GRAY_SCALE_UNIT) - 1
                    if neg_peak_echo_index in range(len(cv_pairs)):
                        neg_peak_echo_velocity = cv_pairs[neg_peak_echo_index][1]
                    else:
                        continue
                    if neg_peak_echo_velocity < maximum_neg_velocity:
                        maximum_neg_velocity = neg_peak_echo_velocity
                # For positive:
                maximum_pos_velocity = 0
                for coord in pos_peaks[pos_idx]:
                    pos_peak_echo_value = unfold_img.getpixel(coord)
                    pos_peak_echo_index = round(pos_peak_echo_value[0] / GRAY_SCALE_UNIT) - 1
                    if pos_peak_echo_index in range(len(cv_pairs)):
                        pos_peak_echo_velocity = cv_pairs[pos_peak_echo_index][1]
                    else:
                        continue
                    if pos_peak_echo_velocity > maximum_pos_velocity:
                        maximum_pos_velocity = pos_peak_echo_velocity
                # Calculate average rotation value
                avg_rotation = (abs(maximum_neg_velocity) + abs(maximum_pos_velocity)) / 2
                # Check with threshold
                if avg_rotation >= MESO_ROTATION_THRESHOLD:
                    # Check valid echo ratio
                    # Calculate mesocyclone logic center
                    logic_center_x = round((neg_center[0] + pos_center[0]) / 2)
                    logic_center_y = round((neg_center[1] + pos_center[1]) / 2)
                    # Get mesocyclone range radius
                    range_radius = round(center_distance)
                    # Iterate meso range to calculate empty and basemaps echo ratio
                    # Note that the valid echoes do not include basemaps filled echoes
                    invalid_echo_num = 0
                    total_in_range_pixel_num = 0
                    for x in range(logic_center_x - range_radius, logic_center_x + range_radius):
                        for y in range(logic_center_y - range_radius, logic_center_y + range_radius):
                            if not math.sqrt((x - logic_center_x) ** 2 + (y - logic_center_y) ** 2) <= range_radius:
                                # Skip coordinate that out of range
                                continue
                            total_in_range_pixel_num += 1
                            # Get pixel value
                            pixel_value = unfold_img.getpixel((x, y))
                            # Calculate gray value index, use second channel RGB value
                            pixel_value_index = round(pixel_value[1] / GRAY_SCALE_UNIT) - 1
                            if pixel_value_index == -1:
                                invalid_echo_num += 1
                    if total_in_range_pixel_num > 0:
                        invalid_echo_ratio = invalid_echo_num / total_in_range_pixel_num
                    else:
                        invalid_echo_ratio = 1
                    # Check with threshold
                    if invalid_echo_ratio <= 1 - VALID_MESO_ECHO_RATIO_THRESHOLD:
                        # Calculate distance from radar center
                        radar_center_distance = math.sqrt(
                            (radar_center[0] - logic_center_x) ** 2 + (radar_center[1] - logic_center_y) ** 2)
                        if radar_center_distance != 0.0:
                            cos_theta = -(logic_center_y - radar_center[1]) / radar_center_distance
                        else:
                            cos_theta = 1
                        theta_radians = math.acos(cos_theta)
                        theta_degrees = math.degrees(theta_radians)
                        if logic_center_x - radar_center[0] < 0:
                            theta_degrees = 360 - theta_degrees
                        mesocyclone_data: MesocycloneInfo = {
                            "storm_num": 0,
                            "logic_center": (logic_center_x, logic_center_y),
                            "radar_distance": radar_center_distance,
                            "radar_angle": theta_degrees,
                            "shear_value": avg_rotation,
                            "neg_center": neg_center,
                            "neg_max_velocity": maximum_neg_velocity,
                            "pos_center": pos_center,
                            "pos_max_velocity": maximum_pos_velocity,
                        }
                        mesocyclone_list.append(mesocyclone_data)

    # Iterate through mesocyclone data list and add storm number
    for storm_index, meso_info in enumerate(mesocyclone_list):
        meso_info["storm_num"] = storm_index

    return mesocyclone_list


def get_group_center(refer_img: Image, echo_group: List[Tuple[int, int]]) -> Optional[Tuple[int, int]]:
    # Get basic data
    cv_pairs = get_color_bar_info("color_velocity_pairs")
    # Iterate through group
    center_x_sum = 0
    center_y_sum = 0
    weight_sum = 0
    for echo_coord in echo_group:
        echo_value = refer_img.getpixel(echo_coord)
        echo_index = round(echo_value[0] / GRAY_SCALE_UNIT) - 1

        weight = abs(cv_pairs[echo_index][1])
        center_x_sum += echo_coord[0] * weight
        center_y_sum += echo_coord[1] * weight
        weight_sum += weight
    # Calculate center coord
    if weight_sum == 0:
        return None
    center_x = round(center_x_sum / weight_sum)
    center_y = round(center_y_sum / weight_sum)
    center = (center_x, center_y)
    return center


def get_meso_debug_img(
        neg_extrema_groups: List[List[Tuple[int, int]]],
        pos_extrema_groups: List[List[Tuple[int, int]]],
        meso_list: List[MesocycloneInfo],
        refer_img: Image,
        debug_img_name: str,
        debug_output_path: Path
):
    # debug image for meso analysis
    meso_debug_img = Image.new("RGB", refer_img.size, (0, 0, 0))

    # merge the two opposite extrema region list
    merged_extremas = neg_extrema_groups + pos_extrema_groups

    # draw extremas
    meso_debug_img = draw_extrema_regions(meso_debug_img, merged_extremas, refer_img)

    debug_img_draw = ImageDraw.Draw(meso_debug_img)
    # Draw mesocyclone extrema region pairs
    for meso_info in meso_list:
        neg_center = meso_info['neg_center']
        # Draw center area with fixed diameter
        for x in range(neg_center[0] - CENTER_DIAMETER, neg_center[0] + CENTER_DIAMETER + 1):
            for y in range(neg_center[1] - CENTER_DIAMETER, neg_center[1] + CENTER_DIAMETER + 1):
                if math.sqrt((x - neg_center[0]) ** 2 + (y - neg_center[1]) ** 2) <= CENTER_DIAMETER:
                    debug_img_draw.point((x, y), (0, 0, 255))
        debug_img_draw.point(neg_center, (0, 255, 0))

        pos_center = meso_info['pos_center']
        for x in range(pos_center[0] - CENTER_DIAMETER, pos_center[0] + CENTER_DIAMETER + 1):
            for y in range(pos_center[1] - CENTER_DIAMETER, pos_center[1] + CENTER_DIAMETER + 1):
                if math.sqrt((x - pos_center[0]) ** 2 + (y - pos_center[1]) ** 2) <= CENTER_DIAMETER:
                    debug_img_draw.point((x, y), (255, 0, 0))
        debug_img_draw.point(pos_center, (0, 255, 0))

        debug_img_draw.line([neg_center, pos_center], fill=(0, 255, 255), width=1)

    # Save debug image: regard the debug_output_path is valid
    debug_img_path = debug_output_path / (debug_img_name + ".png")
    meso_debug_img.save(debug_img_path)
