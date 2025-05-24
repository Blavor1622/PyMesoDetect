from PIL import Image, ImageDraw
import os
import time
import copy
from MesoDetect.DataIO.consts import GRAY_SCALE_UNIT, SURROUNDING_OFFSETS
from MesoDetect.DataIO.radar_config import get_color_bar_info, get_radar_info
from MesoDetect.ImmerseSimulation import meso_condition
from MesoDetect.ImmerseSimulation.meso_condition import AREA_MAXIMUM_THRESHOLD
analysis_result_folder = "peak_analysis/"
analysis_debug_folder = analysis_result_folder + "debug/"


def immerse_analysis(folder_path, preprocessed_img_path):
    """
    Interface of peak analysis
    Args:
        folder_path: path of process result folder
        preprocessed_img_path: path of preprocessed image in inner gray color

    Returns:
        a list that includes two list of peak coordinate groups for neg and pos velocity mode
    """
    start = time.time()
    print("[Info] Start immerse analysis...")
    # Check result folder
    analysis_result_path = folder_path + analysis_result_folder
    if not os.path.exists(analysis_result_path):
        os.makedirs(analysis_result_path)
    debug_folder_path = folder_path + analysis_debug_folder
    if not os.path.exists(debug_folder_path):
        os.makedirs(debug_folder_path)

    # Load preprocessed image
    preprocessed_img = Image.open(preprocessed_img_path)

    # Get layer model of preprocessed image
    layer_model = get_layer_model(preprocessed_img)

    # Get regional peaks
    neg_peak_groups = get_regional_peaks(layer_model, preprocessed_img.size, "neg", debug_folder_path)

    pos_peak_groups = get_regional_peaks(layer_model, preprocessed_img.size, "pos", debug_folder_path)

    # Draw tow mode peak groups debug image
    radar_img_size = get_radar_info("image_size")
    cv_pairs = get_color_bar_info("color_velocity_pairs")
    peak_integrate_img = Image.new("RGB", radar_img_size, (0, 0, 0))
    peak_integrate_draw = ImageDraw.Draw(peak_integrate_img)

    for neg_peak_group in neg_peak_groups:
        for coord in neg_peak_group:
            # Get pixel value
            pixel_value = preprocessed_img.getpixel(coord)
            pixel_value_index = round(pixel_value[0] / GRAY_SCALE_UNIT) - 1
            if pixel_value_index in range(len(cv_pairs)):
                peak_integrate_draw.point(coord, cv_pairs[pixel_value_index][0])

    for pos_peak_group in pos_peak_groups:
        for coord in pos_peak_group:
            # Get pixel value
            pixel_value = preprocessed_img.getpixel(coord)
            pixel_value_index = round(pixel_value[0] / GRAY_SCALE_UNIT) - 1
            if pixel_value_index in range(len(cv_pairs)):
                peak_integrate_draw.point(coord, cv_pairs[pixel_value_index][0])

    peak_integrate_img.save(debug_folder_path + "peak_integration.png")
    end = time.time()
    duration = end - start
    print(f"[Info] Duration of immerse analysis: {duration:.4f} seconds.")

    return neg_peak_groups, pos_peak_groups

#
# def get_peak_group_center(peak_group, refer_img):
#


def get_regional_peaks(layer_model, radar_img_size, mode, debug_folder_path=""):
    """

    Args:
        layer_model: a list of same value echo lists data structure for analysis
        radar_img_size: tuple with two int value of image size
        mode: string value that indicate the velocity mode, only in "neg" or "pos"
        debug_folder_path: path of debug folder

    Returns:

    """
    # Check mode code
    if mode == "neg":
        layer_idx_range = range(0, round(len(layer_model) / 2))
        is_neg = True
    elif mode == "pos":
        layer_idx_range = range(len(layer_model) - 1, round(len(layer_model) / 2) - 1, -1)
        is_neg = False
    else:
        print()
        return
    # Iterate layer model with specific index range
    immerse_img = Image.new("RGB", radar_img_size, (0, 0, 0))
    immerse_draw = ImageDraw.Draw(immerse_img)
    cv_pairs = get_color_bar_info("color_velocity_pairs")
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

        # Draw debug image
        peak_debug_img = Image.new("RGB", radar_img_size, (0, 0, 0))
        peak_debug_draw = ImageDraw.Draw(peak_debug_img)

        for peak_group_pair in peak_groups:
            for coord in peak_group_pair[1]:
                echo_value = immerse_img.getpixel(coord)
                echo_index = round(echo_value[0] / GRAY_SCALE_UNIT) - 1
                peak_debug_draw.point(coord, cv_pairs[echo_index][0])
        # Save debug image
        peak_debug_img.save(debug_folder_path + mode + "_peaks_" + str(layer_idx) + ".png")

    # Meso condition check
    filtered_peak_groups = []
    layer_model_len = len(layer_model)
    for peak_group_pair in peak_groups:
        if meso_condition.check_group_condition(peak_group_pair[1], immerse_img, layer_model_len):
            filtered_peak_groups.append(peak_group_pair[1])
    # Debug filter result
    filter_debug_img = Image.new("RGB", radar_img_size, (0, 0, 0))
    filter_debug_draw = ImageDraw.Draw(filter_debug_img)

    # Iterate through peak groups and draw each group
    for peak_group in filtered_peak_groups:
        for echo_coord in peak_group:
            echo_value = immerse_img.getpixel(echo_coord)
            echo_index = round(echo_value[0] / GRAY_SCALE_UNIT) - 1
            filter_debug_draw.point(echo_coord, cv_pairs[echo_index][0])

    # Save debug result
    filter_debug_img.save(debug_folder_path + mode + "_peak_filtered.png")

    return filtered_peak_groups


def get_layer_model(filled_img):
    """
    Generate a list of same velocity echo coordinate lists that have same length and according index
    value with the color velocity pairs
    :param filled_img: Pillow Image object of filled image
    :return: layer model
    """
    # Get dependency data
    radar_zone = get_radar_info("radar_zone")
    cv_pairs = get_color_bar_info("color_velocity_pairs")

    # Construct empty data structure
    layer_model = []
    for idx in range(len(cv_pairs)):
        layer_model.append([])

    # iterate the filled image
    for x in range(radar_zone[0], radar_zone[1]):
        for y in range(radar_zone[0], radar_zone[1]):
            # get current pixel value
            pixel_value = filled_img.getpixel((x, y))
            gray_index = round(pixel_value[0] * 1.0 / GRAY_SCALE_UNIT) - 1

            if -1 < gray_index < len(cv_pairs):
                layer_model[gray_index].append((x, y))

    return layer_model


"""
        
        if is_neg and layer_idx == 0 or not is_neg and layer_idx == len(layer_model) - 1:
            # Set for no-repeating visiting
            is_visited = set()
            # Iterate through current layer for surrounding analysis
            for echo_coord in layer_model[layer_idx]:
                if echo_coord not in is_visited:
                    is_visited.add(echo_coord)
                    peak_group = [echo_coord]
                    stack = [echo_coord]
                    while stack:
                        latest_coord = stack.pop()
                        for offset in surrounding_offsets:
                            neighbour_coord = (latest_coord[0] + offset[0], latest_coord[1] + offset[1])
                            # Get neighbour pixel value
                            neighbour_value = immerse_img.getpixel(neighbour_coord)
                            # Calculate neighbour gray value index
                            neighbour_index = round(neighbour_value[0] / gray_value_interval) - 1
                            # Check velocity mode for the sequence of comparison
                            if is_neg and 0 <= neighbour_index <= layer_idx:
                                # There is no need for checking the radar range of current neighbour pixel
                                # For only echo pixel will be added into the set and echo pixels always within the radar zone
                                if neighbour_coord not in is_visited:
                                    is_visited.add(neighbour_coord)
                                    peak_group.append(neighbour_coord)
                                    stack.append(neighbour_coord)
                            elif neighbour_index >= layer_idx:
                                if neighbour_coord not in is_visited:
                                    is_visited.add(neighbour_coord)
                                    peak_group.append(neighbour_coord)
                                    stack.append(neighbour_coord)
                    peak_groups.append(peak_group)
        else:
            # Indicate that current time is not the first time and already has a valid peak groups structure
            # Iterate through the peak groups
            new_peak_groups = []
            for former_peak_group in peak_groups:
                # Set for no-repeating visiting
                is_visited = set()
                # Iterate through current layer for surrounding analysis
                for echo_coord in former_peak_group:
                    if echo_coord not in is_visited:
                        is_visited.add(echo_coord)
                        new_peak_group = [echo_coord]
                        stack = [echo_coord]
                        while stack:
                            latest_coord = stack.pop()
                            for offset in surrounding_offsets:
                                neighbour_coord = (latest_coord[0] + offset[0], latest_coord[1] + offset[1])
                                # Get neighbour pixel value
                                neighbour_value = immerse_img.getpixel(neighbour_coord)
                                # Calculate neighbour gray value index
                                neighbour_index = round(neighbour_value[0] / gray_value_interval) - 1
                                # Check velocity mode for the sequence of comparison
                                if is_neg and 0 <= neighbour_index <= layer_idx:
                                    # There is no need for checking the radar range of current neighbour pixel
                                    # For only echo pixel will be added into the set and echo pixels always within the radar zone
                                    if neighbour_coord not in is_visited:
                                        is_visited.add(neighbour_coord)
                                        new_peak_group.append(neighbour_coord)
                                        stack.append(neighbour_coord)
                                elif neighbour_index >= layer_idx:
                                    if neighbour_coord not in is_visited:
                                        is_visited.add(neighbour_coord)
                                        new_peak_group.append(neighbour_coord)
                                        stack.append(neighbour_coord)
                        if len(new_peak_group) <= PEAK_SIZE_THRESHOLD:
                            new_peak_groups.append(new_peak_group)
                        else:
                            new_peak_groups.append(former_peak_group)
"""