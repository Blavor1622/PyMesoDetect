from PIL import Image, ImageDraw
from colorama import Fore, Style
import time
import copy
from MesoDetect.DataIO.consts import GRAY_SCALE_UNIT, SURROUNDING_OFFSETS
from MesoDetect.DataIO.radar_config import get_color_bar_info
from MesoDetect.ImmerseSimulation.consts import AREA_MAXIMUM_THRESHOLD
from MesoDetect.ImmerseSimulation.region_filter import check_region_attributes
from MesoDetect.RadarDenoise.dependencies import get_layer_model
from MesoDetect.ImmerseSimulation.consts import CURRENT_DEBUG_RESULT_FOLDER
from MesoDetect.DataIO.folder_utils import check_output_folder
from typing import List, Tuple, Optional
from pathlib import Path


"""
    Interface of peak_detector
"""
def get_extrema_regions(
        denoised_img: Image,
        debug_output_path: Path,
        enable_debug: bool = False
) -> Optional[Tuple[List[List[Tuple[int, int]]], List[List[Tuple[int, int]]]]]:
    """
    process denoised image and return list of extrema regions coordinate
    Args:
        denoised_img: PIL Image object of denoised image
        enable_debug: boolean flag enabling debug mode for saving analysis result image
        debug_output_path: output location path for analysis result image saving

    Returns:
        a list that includes two list of peak coordinate groups for neg and pos velocity mode
    """
    start = time.time()
    print("[Info] Start immerse simulation analysis...")

    if enable_debug:
        debug_output_path = check_output_folder(debug_output_path, CURRENT_DEBUG_RESULT_FOLDER)
        if debug_output_path is None:
            print(Fore.RED + "[Error] Output folder check failed." + Style.RESET_ALL)
            return None

    # Get layer model of preprocessed image
    try:
        layer_model = get_layer_model(denoised_img)
    except Exception as e:
        print(Fore.RED + f"[Error] Unexpected error: {e}" + Style.RESET_ALL)
        print(Fore.RED + f"[Error] Getting layer model for getting extrema regions failed." + Style.RESET_ALL)
        return None

    # Get regional peaks
    try:
        neg_peak_groups = extrema_region_analysis(layer_model, denoised_img.size, "neg", enable_debug, debug_output_path)
    except Exception as e:
        print(Fore.RED + f"[Error] Unexpected error: {e}" + Style.RESET_ALL)
        print(Fore.RED + f"[Error] Extrema region analysis for `neg` mode failed." + Style.RESET_ALL)
        return None

    try:
        pos_peak_groups = extrema_region_analysis(layer_model, denoised_img.size, "pos", enable_debug, debug_output_path)
    except Exception as e:
        print(Fore.RED + f"[Error] Unexpected error: {e}" + Style.RESET_ALL)
        print(Fore.RED + f"[Error] Extrema region analysis for `pos` mode failed." + Style.RESET_ALL)
        return None

    if enable_debug:
        try:
            integrate_region_groups = neg_peak_groups + pos_peak_groups
            get_region_debug_img(integrate_region_groups, denoised_img, "integrated", debug_output_path)
        except Exception as e:
            print(Fore.RED + f"[Error] Unexpected error: {e}" + Style.RESET_ALL)
            print(Fore.RED + f"[Error] Creating debug image for integrated extrema regions failed." + Style.RESET_ALL)
            return None

    end = time.time()
    duration = end - start
    print(f"[Info] Duration of immerse simulation analysis: {duration:.4f} seconds.")

    return neg_peak_groups, pos_peak_groups


"""
    Internal dependency function
"""
def extrema_region_analysis(
        layer_model: List[List[Tuple[int, int]]],
        radar_img_size: Tuple[int, int],
        mode: str,
        enable_debug: bool,
        debug_output_path: Path
) -> List[List[Tuple[int, int]]]:
    """
    Args:
        layer_model: a list of same value echo lists data structure for analysis
        radar_img_size: tuple with two int value of image size
        mode: string value that indicate the velocity mode, only in "neg" or "pos"
        enable_debug: boolean flag, True for enabling debug mode and False for disabling
        debug_output_path: path of debug folder
    """
    # Check mode code
    if mode == "neg":
        layer_idx_range = range(0, round(len(layer_model) / 2))
        is_neg = True
    elif mode == "pos":
        layer_idx_range = range(len(layer_model) - 1, round(len(layer_model) / 2) - 1, -1)
        is_neg = False
    else:
        raise ValueError(f"[Error] Invalid mode code: {mode} for extrema regions analysis.")
    # Iterate layer model with specific index range
    immerse_img = Image.new("RGB", radar_img_size, (0, 0, 0))
    immerse_draw = ImageDraw.Draw(immerse_img)
    peak_groups = []
    # items in this list have structure like (flag, echo_groups)
    # the flag is an int value that only in 0 or 1
    # echo_groups is the list of coordinates
    for layer_idx in layer_idx_range:
        # Calculate current layer value
        current_layer_value = (layer_idx + 1) * GRAY_SCALE_UNIT
        current_layer_color = (current_layer_value, current_layer_value, current_layer_value)

        # Draw current layer echoes into the immerse image
        for echo_coord in layer_model[layer_idx]:
            immerse_draw.point(echo_coord, current_layer_color)

        # Check whether is the first time or not
        new_peak_groups = []
        is_former_peak_added = set()
        # First check peak groups from last layer
        for former_peak_group_pair in peak_groups:
            # Check the current former peak group and merge it
            if len(former_peak_group_pair[1]) == 0:
                # Skip empty peak group
                continue
            if former_peak_group_pair[0] == 1:
                new_peak_groups.append(former_peak_group_pair)
                continue
            # Check whether peak group that can be extended has been visited or not
            if former_peak_group_pair[1][0] in is_former_peak_added:
                # Indicate that current peak group has been added into the new peak group
                # Skip this group
                continue
            # copy the former group content
            new_peak_group = copy.deepcopy(former_peak_group_pair[1])
            is_visited = set()
            is_exceed = False
            for echo_coord in new_peak_group:
                if echo_coord not in is_visited:
                    is_visited.add(echo_coord)
                    stack = [echo_coord]
                    while stack:
                        current_coord = stack.pop()
                        for offset in SURROUNDING_OFFSETS:
                            neighbour_coord = (current_coord[0] + offset[0], current_coord[1] + offset[1])
                            neighbour_value = immerse_img.getpixel(neighbour_coord)
                            neighbour_index = round(neighbour_value[0] / GRAY_SCALE_UNIT) - 1
                            # Check neighbour index value
                            if is_neg and 0 <= neighbour_index <= layer_idx:
                                if neighbour_coord not in is_visited:
                                    is_visited.add(neighbour_coord)
                                    stack.append(neighbour_coord)
                                    new_peak_group.append(neighbour_coord)
                            elif not is_neg and neighbour_index >= layer_idx:
                                if neighbour_coord not in is_visited:
                                    is_visited.add(neighbour_coord)
                                    stack.append(neighbour_coord)
                                    new_peak_group.append(neighbour_coord)
                        if len(new_peak_group) > AREA_MAXIMUM_THRESHOLD:
                            is_exceed = True
                            break
            # Check whether the peak group has extended or not
            if not is_exceed:
                # Indicate that current peak group after extension satisfies the condition
                # Add this group into new list
                new_peak_groups.append((0, new_peak_group))
                # Mark former peak group that is included in current group
                for fpg_pair in peak_groups:
                    # Skip peak group that has been marked terminating extension
                    if fpg_pair[0] == 1:
                        continue
                    # Skip empty peak group
                    if len(fpg_pair[1]) == 0:
                        continue
                    # Extract a group instance to check inclusion relationship
                    if fpg_pair[1][0] in new_peak_group:
                        # Indicate that current peak group also included in the new peak group
                        for coord in fpg_pair[1]:
                            is_former_peak_added.add(coord)
            else:
                for fpg_pair in peak_groups:
                    # Skip peak group that has been marked terminating extension
                    if fpg_pair[0] == 1:
                        continue
                    # Skip empty peak group
                    if len(fpg_pair[1]) == 0:
                        continue
                    # Extract a group instance to check inclusion relationship
                    if fpg_pair[1][0] in new_peak_group:
                        # Indicate that current peak group also included in the new peak group
                        for coord in fpg_pair[1]:
                            is_former_peak_added.add(coord)
                        new_peak_groups.append((1, fpg_pair[1]))
        # Then check new layer peak groups that generated by current layer echoes
        # Iterate current layer echoes
        is_visited = set()
        for echo_coord in layer_model[layer_idx]:
            if echo_coord not in is_visited:
                is_visited.add(echo_coord)
                new_init_peak_group = [echo_coord]
                stack = [echo_coord]
                is_not_isolated = False
                while stack:
                    current_coord = stack.pop()
                    for offset in SURROUNDING_OFFSETS:
                        neighbour_coord = (current_coord[0] + offset[0], current_coord[1] + offset[1])
                        neighbour_value = immerse_img.getpixel(neighbour_coord)
                        neighbour_index = round(neighbour_value[0] / GRAY_SCALE_UNIT) - 1
                        if neighbour_index == layer_idx:
                            if neighbour_coord not in is_visited:
                                is_visited.add(neighbour_coord)
                                stack.append(neighbour_coord)
                                new_init_peak_group.append(neighbour_coord)
                        elif neighbour_index != -1:
                            # Indicates that current group is not an isolated group
                            is_not_isolated = True
                # First check whether the group is isolated or not
                if not is_not_isolated:
                    # Check new initial peak group size with threshold
                    # Note that here use simple condition in case too strict condition check causes over-filter
                    if len(new_init_peak_group) <= AREA_MAXIMUM_THRESHOLD:
                        new_peak_groups.append((0, new_init_peak_group))

        # Update peak group
        peak_groups = new_peak_groups

        # Draw debug image if enable debug mode
        if enable_debug:
            # Create a peak region groups for debug image generation
            peak_debug_groups = []
            for peak_group_pair in peak_groups:
                peak_debug_groups.append(peak_group_pair[1])
            get_region_debug_img(peak_debug_groups, immerse_img, mode + "_peaks_" + str(layer_idx), debug_output_path)

    # Meso condition check
    filtered_peak_groups = []
    layer_model_len = len(layer_model)
    for peak_group_pair in peak_groups:
        if check_region_attributes(peak_group_pair[1], immerse_img, layer_model_len):
            filtered_peak_groups.append(peak_group_pair[1])

    if enable_debug:
        get_region_debug_img(filtered_peak_groups, immerse_img, mode + "_peak_filtered", debug_output_path)

    return filtered_peak_groups


def get_region_debug_img(region_groups: List[List[Tuple[int, int]]], refer_img: Image, debug_img_name: str, debug_output_path: Path):
    # Create a debug image
    debug_img = Image.new("RGB", refer_img.size, (0, 0, 0))

    # Draw extrema regions
    debug_img = draw_extrema_regions(debug_img, region_groups, refer_img)

    # Save debug image: regard the debug_output_path is valid
    debug_img_path = debug_output_path / (debug_img_name + ".png")
    debug_img.save(debug_img_path)


def draw_extrema_regions(debug_img: Image, region_groups: List[List[Tuple[int, int]]], refer_img: Image) -> Image:
    # Draw region groups on debug image
    cv_pairs = get_color_bar_info("color_velocity_pairs")
    debug_img_draw = ImageDraw.Draw(debug_img)
    for region_group in region_groups:
        for coord in region_group:
            # Get pixel value
            pixel_value = refer_img.getpixel(coord)
            pixel_value_index = round(pixel_value[0] / GRAY_SCALE_UNIT) - 1
            if pixel_value_index in range(len(cv_pairs)):
                debug_img_draw.point(coord, cv_pairs[pixel_value_index][0])
    return debug_img