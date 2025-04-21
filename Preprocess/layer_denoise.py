"""
given a new algorithm for solving the velocity folded problem:
use layer filling as well as layer distance to detect the velocity folded phenomenon
"""
from PIL import Image, ImageDraw
import utils
import os
import time
import numpy as np
from skimage.segmentation import flood_fill

"""
denoise:
    for each small group
        calculate below value index
        if not empty and not base echo
            if not exceed GAP_THRESHOLD
                draw group
            else
                skip current group
        if not empty and is base echo
            calculate surrounding value index (excluding base echoes)
            if surrounding not empty
                if not not exceed GAP_THRESHOLD
                    draw group with original color value
                else 
                    draw group with average color value
            else
                use below value index (actually point to base echo color value)
                if not exceed GAP_THRESHOLD
                    draw group
                else
                    skip current group
        else
            skip small isolate echo group
"""


analysis_folder = "layer_fill/"
debug_folder = "layer_debug/"
group_size_threshold = 15
layer_gap_threshold = 2.2
unfold_gap_threshold = 6.5
surrounded_fill_threshold = 0.9
folded_echo_layer_num = 2
opposite_surrounded_threshold = 0.1


def layer_analysis(folder_path, narrow_filled_path):
    """
    Apply layer filling algorithm to unfold velocity as well as denoising
    Args:
        folder_path: path of result images folder
        narrow_filled_path: path of narrow filled gray image

    Returns: path of analysis result image with string format

    """
    start = time.time()
    print("[Info] Start layer filling analysis...")
    # Check result folder
    analysis_result_folder = folder_path + analysis_folder
    if not os.path.exists(analysis_result_folder):
        os.makedirs(analysis_result_folder)
    analysis_debug_folder = analysis_result_folder + debug_folder
    if not os.path.exists(analysis_debug_folder):
        os.makedirs(analysis_debug_folder)
    # Load images
    fill_img = Image.open(narrow_filled_path)
    # Get const data
    layer_model = get_layer_model(fill_img)
    # Get denoise image
    neg_denoise_img = get_denoise_img(fill_img, layer_model, "neg", analysis_debug_folder)
    pos_denoise_img = get_denoise_img(fill_img, layer_model, "pos", analysis_debug_folder)

    neg_denoise_img_path = analysis_result_folder + "neg_denoised.png"
    pos_denoise_img_path = analysis_result_folder + "pos_denoised.png"

    neg_denoise_img.save(neg_denoise_img_path)
    pos_denoise_img.save(pos_denoise_img_path)

    integrate_img = velocity_integrate(neg_denoise_img, pos_denoise_img, analysis_debug_folder)
    integrate_img_path = analysis_result_folder + "denoised_integrate.png"

    integrate_img.save(integrate_img_path)

    unfold_img = velocity_unfold(integrate_img, analysis_debug_folder)
    unfold_img_path = analysis_result_folder + "unfold.png"
    unfold_img.save(unfold_img_path)

    end = time.time()
    duration = end - start
    print(f"[Info] Duration of layer filling analysis: {duration:.4f} seconds.")
    return neg_denoise_img_path, pos_denoise_img_path, integrate_img_path, unfold_img_path


def velocity_unfold(integrated_img, debug_result_folder=""):
    """

    Args:
        integrated_img:
        debug_result_folder:

    Returns:

    """
    # Get layer model of integrated image
    layer_model = get_layer_model(integrated_img)
    # Get basic data
    gray_value_interval = utils.gray_value_interval
    half_index = round(len(layer_model) / 2) - 1
    surrounding_offsets = utils.surrounding_offsets
    # Create a image for the unfolding result
    # Note that using copy to separate the tow mode process in case of interference
    unfold_img = integrated_img.copy()
    unfold_draw = ImageDraw.Draw(unfold_img)

    # Debug image
    debug_img = Image.new("RGB", integrated_img.size, (0, 0, 0))
    debug_draw = ImageDraw.Draw(debug_img)

    # Unfold process for neg mode
    neg_target_indexes = range(len(layer_model) - folded_echo_layer_num, len(layer_model))
    unfolded_value = (0 + 1) * gray_value_interval
    unfolded_color = (unfolded_value, unfolded_value, unfolded_value)
    for neg_tar_idx in neg_target_indexes:
        # Get echo groups of current target echoes
        echo_groups = get_echo_groups(integrated_img, layer_model[neg_tar_idx])
        # Analise each group's surrounding
        for echo_group in echo_groups:
            surroundings = set()
            valid_surrounding_indexes = []
            opposite_mode_indexes = []
            for coord in echo_group:
                for offset in surrounding_offsets:
                    neighbour_coord = (coord[0] + offset[0], coord[1] + offset[1])
                    neighbour_value = integrated_img.getpixel(neighbour_coord)
                    neighbour_index = round(neighbour_value[0] / gray_value_interval) - 1
                    if neighbour_index != neg_tar_idx:
                        if neighbour_coord not in surroundings:
                            surroundings.add(neighbour_coord)
                            if neighbour_index >= 0:
                                valid_surrounding_indexes.append(neighbour_index)
                                if neighbour_index <= half_index:
                                    opposite_mode_indexes.append(neighbour_index)

            if (len(valid_surrounding_indexes) > 0
                and len(valid_surrounding_indexes) == len(opposite_mode_indexes)):
                # Indicate that current echo groups only has opposite echo surroundings
                # Check surrounding threshold
                opposite_surrounded_ratio = len(opposite_mode_indexes) / len(surroundings)
                if opposite_surrounded_ratio >= opposite_surrounded_threshold:
                    for coord in echo_group:
                        unfold_draw.point(coord, unfolded_color)
                        debug_draw.point(coord, (0, 0, 255))
    # Unfold process for pos mode
    pos_target_indexes = range(0 + folded_echo_layer_num - 1, -1, -1)
    unfolded_value = (len(layer_model) - 1 + 1) * gray_value_interval
    unfolded_color = (unfolded_value, unfolded_value, unfolded_value)
    for pos_tar_idx in pos_target_indexes:
        # Get echo groups of current target echoes
        echo_groups = get_echo_groups(integrated_img, layer_model[pos_tar_idx])
        # Analise each group's surrounding
        for echo_group in echo_groups:
            surroundings = set()
            valid_surrounding_indexes = []
            opposite_mode_indexes = []
            for coord in echo_group:
                for offset in surrounding_offsets:
                    neighbour_coord = (coord[0] + offset[0], coord[1] + offset[1])
                    neighbour_value = integrated_img.getpixel(neighbour_coord)
                    neighbour_index = round(neighbour_value[0] / gray_value_interval) - 1
                    if neighbour_index != pos_tar_idx:
                        if neighbour_coord not in surroundings:
                            surroundings.add(neighbour_coord)
                            if neighbour_index >= 0:
                                valid_surrounding_indexes.append(neighbour_index)
                                if neighbour_index >= half_index + 1:
                                    opposite_mode_indexes.append(neighbour_index)

            if (len(valid_surrounding_indexes) > 0
                    and len(valid_surrounding_indexes) == len(opposite_mode_indexes)):
                # Indicate that current echo groups only has opposite echo surroundings
                # Check surrounding threshold
                opposite_surrounded_ratio = len(opposite_mode_indexes) / len(surroundings)
                if opposite_surrounded_ratio >= opposite_surrounded_threshold:
                    for coord in echo_group:
                        unfold_draw.point(coord, unfolded_color)
                        debug_draw.point(coord, (255, 0, 0))
    # Save debug image
    debug_img.save(debug_result_folder + "unfold_debug.png")
    return unfold_img


def get_denoise_img(fill_img, layer_model, mode, debug_result_folder=""):
    """
    Layer process and return a denoise image for given mode code
    Args:
        fill_img: PIL Image Object of narrow filled image
        layer_model: list of layer echoes
        mode: string that indicates the velocity mode
        debug_result_folder: debug result folder

    Returns:
    PIL Image object of a denoised image
    """
    # Get base echo image
    denoise_img = get_base_echo_img(layer_model, fill_img.size, mode)
    denoise_img.save(debug_result_folder + mode + "_base.png")

    # Check mode code
    if mode == "neg":
        base_index = round(len(layer_model) / 2) - 1
        layer_range = range(base_index, -1, -1)
        is_reverse = True
    elif mode == "pos":
        base_index = round(len(layer_model) / 2)
        layer_range = range(base_index, len(layer_model))
        is_reverse = False
    else:
        print()
        return
    # Execute layer analysis
    gray_value_interval = utils.gray_value_interval
    denoise_draw = ImageDraw.Draw(denoise_img)
    small_echo_groups = []
    for layer_idx in layer_range:
        # Get echo groups for current layer
        echo_groups = get_echo_groups(fill_img, layer_model[layer_idx])
        # Calculate gray color value for current layer
        layer_echo_value = (layer_idx + 1) * gray_value_interval
        echo_color = (layer_echo_value, layer_echo_value, layer_echo_value)
        # Create an inner filling refer image
        inner_fill_refer_img = Image.new("RGB", fill_img.size, (0, 0, 0))
        inner_fill_refer_draw = ImageDraw.Draw(inner_fill_refer_img)
        # Draw echo groups that bigger than size threshold
        for echo_group in echo_groups:
            # Huge echo skip denoise
            if len(echo_group) >= group_size_threshold:
                for echo_coordinate in echo_group:
                    denoise_draw.point(echo_coordinate, echo_color)
                    inner_fill_refer_draw.point(echo_coordinate, echo_color)
            else:
                if len(echo_group) > 0:
                    small_echo_groups.append(echo_group)
        # Execute inner filling
        denoise_img = inner_filling(inner_fill_refer_img, echo_color, denoise_img)
        denoise_draw = ImageDraw.Draw(denoise_img)
    # Save debug image
    denoise_img.save(debug_result_folder + mode + "_smooth.png")

    # Analise small echo groups that might contain noise echo
    surrounding_offsets = utils.surrounding_offsets
    for small_group in small_echo_groups:
        # Get below echo value of current group
        below_value = denoise_img.getpixel(small_group[0])
        # Calculate below value index
        below_value_index = round(1.0 * below_value[1] / gray_value_interval) - 1
        # Calculate small group actual value index
        current_group_value = fill_img.getpixel(small_group[0])
        current_group_index = round(1.0 * current_group_value[0] / gray_value_interval) - 1
        if below_value_index >= 0:
            # indicate that no empty base or base echo
            # Check value index grap
            if not is_reverse and 0 <= current_group_index - below_value_index <= layer_gap_threshold:
                for echo_coordinate in small_group:
                    denoise_draw.point(echo_coordinate, current_group_value)
            elif is_reverse and 0 <= below_value_index - current_group_index <= layer_gap_threshold:
                for echo_coordinate in small_group:
                    denoise_draw.point(echo_coordinate, current_group_value)
        else:
            base_below_index = round(1.0 * below_value[0] / gray_value_interval) - 1
            if base_below_index >= 0:
                # Indicate that no empty but is base echo
                # Get surroundings
                valid_surroundings = set()
                valid_surrounding_indexes = []
                for echo_coordinate in small_group:
                    # Get neighbour color analysis
                    for offset in surrounding_offsets:
                        neighbour_coordinate = (echo_coordinate[0] + offset[0], echo_coordinate[1] + offset[1])
                        neighbour_value = denoise_img.getpixel(neighbour_coordinate)[1]
                        neighbour_index = round(1.0 * neighbour_value / gray_value_interval) - 1
                        if neighbour_index >= 0:
                            # Indicate that current neighbour is a valid surrounding
                            if neighbour_coordinate not in valid_surroundings:
                                valid_surroundings.add(neighbour_coordinate)
                                valid_surrounding_indexes.append(neighbour_index)
                if len(valid_surrounding_indexes) > 0:
                    # indicate that there are valid surrounding for current small group
                    # Calculate average value index
                    avg_surrounding_index = sum(valid_surrounding_indexes) / len(valid_surrounding_indexes)
                    # Check with threshold
                    if abs(current_group_index - avg_surrounding_index) <= layer_gap_threshold:
                        for echo_coordinate in small_group:
                            denoise_draw.point(echo_coordinate, current_group_value)
                    else:
                        # Indicate that current small group exceed the gap threshold with valid surroundings
                        # Calculate approximate average value index
                        round_avg_index = round(avg_surrounding_index)
                        round_avg_value = (round_avg_index + 1) * gray_value_interval
                        for echo_coordinate in small_group:
                            denoise_draw.point(echo_coordinate, (round_avg_value, round_avg_value, round_avg_value))
                else:
                    # Indicate that current small group has not valid surroundings
                    # Check with base below index
                    if abs(current_group_index - base_below_index) <= layer_gap_threshold:
                        for echo_coordinate in small_group:
                            denoise_draw.point(echo_coordinate, current_group_value)

    # Filling base echo
    denoise_img = base_echo_fill(denoise_img, len(layer_model), mode)
    return denoise_img


def velocity_integrate(neg_img, pos_img, debug_result_folder=""):
    """
    Integrate neg and pos velocity mode denoise result image into complete radar image
    Args:
        neg_img: PIL Image object of neg denoise image
        pos_img: PIL Image object of pos denoise image
        debug_result_folder: folder path for containing debug result image

    Returns:
    PIL Image object of integrated image
    """
    # Create a integration result image
    integrate_img = Image.new("RGB", neg_img.size, (0, 0, 0))
    integrate_draw = ImageDraw.Draw(integrate_img)

    # Iterate through both neg and pos image to get uncrossed echoes
    radar_zone = utils.get_radar_info("radar_zone")
    gray_value_interval = utils.gray_value_interval
    crossed_echoes = []
    for x in range(radar_zone[0], radar_zone[1]):
        for y in range(radar_zone[0], radar_zone[1]):
            # Get pixel value for both neg and pos image
            neg_pixel_value = neg_img.getpixel((x, y))
            pos_pixel_value = pos_img.getpixel((x, y))
            # Calculate gray value index of the pixel value
            neg_pixel_index = round(neg_pixel_value[0] / gray_value_interval) - 1
            pos_pixel_index = round(pos_pixel_value[0] / gray_value_interval) - 1
            # Check both index to decide echo get crossed or not
            if neg_pixel_index != -1 and pos_pixel_index == -1:
                integrate_draw.point((x, y), neg_pixel_value)
            elif neg_pixel_index == -1 and pos_pixel_index != -1:
                integrate_draw.point((x, y), pos_pixel_value)
            elif neg_pixel_index != -1 and pos_pixel_index != -1:
                crossed_echoes.append((x, y))

    # Create a refer image for echo grouping
    refer_img = Image.new("RGB", neg_img.size, (0, 0, 0))
    refer_draw = ImageDraw.Draw(refer_img)
    for echo_coordinate in crossed_echoes:
        refer_draw.point(echo_coordinate, (238, 0, 0))
    refer_img.save(debug_result_folder + "crossed_refer.png")

    # Get crossed echo groups
    crossed_groups = get_echo_groups(refer_img, crossed_echoes)

    # Debug image for surrounding analysis
    surrounding_debug_img = Image.new("RGB", neg_img.size, (0, 0, 0))
    surrounding_debug_draw = ImageDraw.Draw(surrounding_debug_img)

    # Iterate each group and check the surroundings
    cv_pairs = utils.get_color_bar_info("color_velocity_pairs")
    pos_unfold_idx = len(cv_pairs) - 1
    surrounding_offsets = utils.surrounding_offsets
    for crossed_group in crossed_groups:
        # Get unrepeated surroundings
        surrounding_coords = set()
        for echo_coordinate in crossed_group:
            for offset in surrounding_offsets:
                # Get neighbour coordinate with offset
                neighbour_coordinate = (echo_coordinate[0] + offset[0], echo_coordinate[1] + offset[1])
                # Get neighbour value
                neighbour_value = refer_img.getpixel(neighbour_coordinate)
                neighbour_index = round(neighbour_value[0] / gray_value_interval) - 1
                # Surrounding check
                if neighbour_index == -1:
                    if neighbour_coordinate not in surrounding_coords:
                        surrounding_coords.add(neighbour_coordinate)
        if len(surrounding_coords) == 0:
            continue
        # Just need to get surroundings in one single velocity mode image, by default use neg img
        valid_surroundings = []
        for coord in surrounding_coords:
            # Get pixel value from neg image
            surrounding_value = neg_img.getpixel(coord)
            # Calculate index value
            surrounding_index = round(surrounding_value[0] / gray_value_interval) - 1
            if surrounding_index >= 0:
                valid_surroundings.append(surrounding_index)
        # Calculate valid surrounding ratio
        neg_surrounded_ratio = len(valid_surroundings) / len(surrounding_coords)
        # Check ratio to decide keep whose echo
        if neg_surrounded_ratio >= surrounded_fill_threshold - 0.05:
            # Indicates that neg echo is the base and pos is going to add upon it
            if len(crossed_group) < group_size_threshold:
                for coord in crossed_group:
                    neg_pixel_value = neg_img.getpixel(coord)
                    integrate_draw.point(coord, neg_pixel_value)
                    surrounding_debug_draw.point(coord, neg_pixel_value)
            else:
                # Calculate average layer gap of the crossed echo
                total_gap_sum = 0
                for coord in crossed_group:
                    # Get pixel value
                    neg_pixel_value = neg_img.getpixel(coord)
                    pos_pixel_value = pos_img.getpixel(coord)
                    # Calculate value index
                    neg_pixel_index = round(neg_pixel_value[0] / gray_value_interval) - 1
                    pos_pixel_index = round(pos_pixel_value[0] / gray_value_interval) - 1
                    # Calculate distance
                    layer_gap = pos_pixel_index - neg_pixel_index
                    total_gap_sum += layer_gap
                avg_layer_gap = total_gap_sum / len(crossed_group)
                if avg_layer_gap >= unfold_gap_threshold:
                    # Indicate that current group is folded and on neg base
                    for coord in crossed_group:
                        neg_pixel_value = (0 + 1) * gray_value_interval
                        neg_pixel_color = (neg_pixel_value, 0, neg_pixel_value)
                        integrate_draw.point(coord, neg_pixel_color)
                        surrounding_debug_draw.point(coord, neg_pixel_color)
                else:
                    # Indicate that current group is not folded
                    for coord in crossed_group:
                        pos_pixel_value = pos_img.getpixel(coord)
                        integrate_draw.point(coord, pos_pixel_value)
                        surrounding_debug_draw.point(coord, pos_pixel_value)

        else:
            if len(crossed_group) < group_size_threshold:
                for coord in crossed_group:
                    pos_pixel_value = pos_img.getpixel(coord)
                    integrate_draw.point(coord, pos_pixel_value)
                    surrounding_debug_draw.point(coord, pos_pixel_value)
            else:
                # Calculate average layer gap of the crossed echo
                total_gap_sum = 0
                for coord in crossed_group:
                    # Get pixel value
                    neg_pixel_value = neg_img.getpixel(coord)
                    pos_pixel_value = pos_img.getpixel(coord)
                    # Calculate value index
                    neg_pixel_index = round(neg_pixel_value[0] / gray_value_interval) - 1
                    pos_pixel_index = round(pos_pixel_value[0] / gray_value_interval) - 1
                    # Calculate distance
                    layer_gap = pos_pixel_index - neg_pixel_index
                    total_gap_sum += layer_gap
                avg_layer_gap = total_gap_sum / len(crossed_group)
                if avg_layer_gap >= unfold_gap_threshold:
                    # Indicate that current group is folded and on pos base
                    for coord in crossed_group:
                        pos_pixel_value = (pos_unfold_idx + 1) * gray_value_interval
                        pos_pixel_color = (pos_pixel_value, 0, pos_pixel_value)
                        integrate_draw.point(coord, pos_pixel_color)
                        surrounding_debug_draw.point(coord, pos_pixel_color)
                else:
                    # Indicate that current group is not folded
                    for coord in crossed_group:
                        neg_pixel_value = neg_img.getpixel(coord)
                        integrate_draw.point(coord, neg_pixel_value)
                        surrounding_debug_draw.point(coord, neg_pixel_value)
    # Save surrounding debug image
    surrounding_debug_img.save(debug_result_folder + "surrounding_fill.png")

    return integrate_img


def base_echo_fill(gray_img, layer_model_len, mode):
    # Check mode code
    gray_value_interval = utils.gray_value_interval
    if mode == "neg":
        base_index = round(layer_model_len / 2) - 1
    elif mode == "pos":
        base_index = round(layer_model_len / 2)
    else:
        print()
        return
    base_color_value = (base_index + 1) * gray_value_interval
    base_color = (base_color_value, base_color_value, base_color_value)
    # Create a refer image for grouping
    refer_img = Image.new("RGB", gray_img.size, (0, 0, 0))
    refer_draw = ImageDraw.Draw(refer_img)

    # Iterate radar zone to get need fill area
    radar_zone = utils.get_radar_info("radar_zone")
    base_echo_list = []
    for x in range(radar_zone[0], radar_zone[1]):
        for y in range(radar_zone[0], radar_zone[1]):
            # Get current pixel value
            pixel_value = gray_img.getpixel((x, y))
            # Calculate gray value index
            pixel_index_0 = round(pixel_value[0] / gray_value_interval) - 1
            pixel_index_1 = round(pixel_value[1] / gray_value_interval) - 1
            # Check whether is base echo or not
            if pixel_index_0 != pixel_index_1:
                base_echo_list.append((x, y))
                refer_draw.point((x, y), base_color)

    # Get base echo groups
    base_echo_groups = get_echo_groups(refer_img, base_echo_list)
    surrounding_offsets = utils.surrounding_offsets
    # Analise each group's surrounding
    gray_draw = ImageDraw.Draw(gray_img)
    for echo_group in base_echo_groups:
        surroundings = set()
        valid_surrounding_indexes = []
        for echo_coordinate in echo_group:
            for offset in surrounding_offsets:
                neighbour_coordinate = (echo_coordinate[0] + offset[0], echo_coordinate[1] + offset[1])
                neighbour_value = gray_img.getpixel(neighbour_coordinate)
                neighbour_index_0 = round(neighbour_value[0] / gray_value_interval) - 1
                neighbour_index_1 = round(neighbour_value[1] / gray_value_interval) - 1
                if neighbour_index_0 == neighbour_index_1:
                    if neighbour_coordinate not in surroundings:
                        surroundings.add(neighbour_coordinate)
                        if neighbour_index_0 >= 0:
                            valid_surrounding_indexes.append(neighbour_index_0)
        if len(surroundings) == 0:
            continue
        surrounded_ratio = len(valid_surrounding_indexes) / len(surroundings)
        if surrounded_ratio >= surrounded_fill_threshold:
            # Calculate average surrounding index
            avg_surrounding_idx = sum(valid_surrounding_indexes) / len(valid_surrounding_indexes)
            round_avg_idx = round(avg_surrounding_idx)
            avg_value = (round_avg_idx + 1) * gray_value_interval
            for echo_coordinate in echo_group:
                gray_draw.point(echo_coordinate, (avg_value, 0, 0))
    return gray_img


def get_base_echo_img(layer_model, radar_img_size, mode):
    """
    Generate a base velocity image for layer analysis
    Args:
        layer_model: list of layer echoes
        radar_img_size: size of radar image
        mode: a string that indicate the velocity mode

    Returns:
        A PIL Image Object of base velocity image
    """
    # Check mode code
    if mode == "neg":
        base_index = round(len(layer_model) / 2) - 1
        layer_range = range(base_index, -1, -1)
    elif mode == "pos":
        base_index = round(len(layer_model) / 2)
        layer_range = range(base_index, len(layer_model))
    else:
        print()
        return
    # Create an empty image for drawing base echo
    base_img = Image.new("RGB", radar_img_size, (0, 0, 0))
    base_draw = ImageDraw.Draw(base_img)
    # Get basic values
    gray_value_interval = utils.gray_value_interval
    base_value = gray_value_interval * (base_index + 1)
    base_color = (base_value, 0, base_value)
    for layer_idx in layer_range:
        for echo_coordinate in layer_model[layer_idx]:
            base_draw.point(echo_coordinate, base_color)
    # Execute inner filling
    base_img = inner_filling(base_img, base_color, base_img)
    # Get echo pixels
    echo_pixel_list = []
    radar_zone = utils.get_radar_info("radar_zone")
    for x in range(radar_zone[0], radar_zone[1]):
        for y in range(radar_zone[0], radar_zone[1]):
            # Get current pixel value
            pixel_coordinate = (x, y)
            pixel_value = base_img.getpixel(pixel_coordinate)[0]
            # Calculate color value index of the pixel
            pixel_index = round(1.0 * pixel_value / gray_value_interval) - 1
            if pixel_index != -1:
                echo_pixel_list.append(pixel_coordinate)
    # Get echo groups
    echo_groups = get_echo_groups(base_img, echo_pixel_list)
    # Remove echo groups that smaller than the group size threshold
    removed_groups = []
    for echo_group in echo_groups:
        if len(echo_group) < group_size_threshold:
            removed_groups.append(echo_group)
    # Cover the groups with empty value for removing
    base_draw = ImageDraw.Draw(base_img)
    for echo_group in removed_groups:
        for echo_coordinate in echo_group:
            base_draw.point(echo_coordinate, (0, 0, 0))
    # Return result image
    return base_img


def get_echo_groups(refer_img, coordinate_list):
    """
    a utility function that divides the given coordinate_list
    and then return a list of connected components
    :param refer_img: a Pillow Image object that used for checking connected relationship of echoes
    :param coordinate_list: list of coordinate that might have several connected component
    :return: a list of connected components
    """
    if len(coordinate_list) == 0:
        return [[]]
    # get neighbour coordinate offset
    neighbour_offsets = utils.surrounding_offsets

    # Get radar zone
    radar_zone = utils.get_radar_info("radar_zone")
    gray_value_interval = utils.gray_value_interval

    # Extract gray value index of current point
    target_value = refer_img.getpixel(coordinate_list[0])[0]
    target_index = round(1.0 * target_value / gray_value_interval) - 1

    components = []
    visited = set()
    for point in coordinate_list:
        if point not in visited:
            visited.add(point)
            stack = [point]
            component = [point]

            while stack:
                current_point = stack.pop()

                # get surrounding pixel values
                for offset in neighbour_offsets:
                    # ger neighbour pixel coordinate
                    neighbour = (current_point[0] + offset[0], current_point[1] + offset[1])
                    # radar scale check
                    if (radar_zone[0] <= neighbour[0] <= radar_zone[1]
                            and radar_zone[0] <= neighbour[1] <= radar_zone[1]):
                        neighbour_value = refer_img.getpixel(neighbour)[0]
                        if round(neighbour_value * 1.0 / gray_value_interval) - 1 == target_index:
                            # Mean that neighbour value similar to target value (slight difference is allowed)
                            if neighbour not in visited:
                                visited.add(neighbour)
                                component.append(neighbour)
                                stack.append(neighbour)
            components.append(component)
    return components


def inner_filling(refer_img, fill_color, fill_img):
    """
    Flooding outer blanks in given gray image and fill inner blanks of the image with
    gray color that gray value index indicates
    :param refer_img: PIL Image object in RGB mode with gray color that indicating inner relationship
    :param fill_color: RGB color for filling
    :param fill_img: PIL IMage object in RGB mode that need inner filling
    :return: a PIL Image object of an inner filled gray image
    """
    # Check valid fill color
    if len(fill_color) != 3:
        print(f"[Error] Invalid fill color: {fill_color} for `inner_filling`.")
        return
    # Get basic data
    gray_value_interval = utils.gray_value_interval
    radar_zone = utils.get_radar_info("radar_zone")

    # Convert RGB Image into gray image numpy array
    gray_img_arr = np.array(refer_img.convert("L"))

    # flood fill the array from point (0, 0) with value 255
    flooded_arr = flood_fill(gray_img_arr, (0, 0), new_value=255, connectivity=1)

    # Get interested zone border of the image
    top, left = radar_zone[0], radar_zone[0]
    bottom, right = radar_zone[1], radar_zone[1]

    # Convert original gray RGB PIL image into numpy array
    frame_arr = np.array(fill_img)

    # Extract radar zone from the array
    flooded_arr_sub = flooded_arr[top:bottom, left:right]  # shape: (subH, subW)
    frame_arr_sub = frame_arr[top:bottom, left:right, :]  # shape: (subH, subW, 3)

    # Compute the gray color index in one shot
    color_index_arr = np.round(flooded_arr_sub.astype(float) / gray_value_interval) - 1

    # Identify pixels where the index == -1
    mask = (color_index_arr == -1)

    # Fill those pixels in the frame_sub
    frame_arr_sub[mask] = [fill_color[0], fill_color[1], fill_color[2]]

    # Convert back to PIL and save
    fill_img = Image.fromarray(frame_arr, mode="RGB")
    return fill_img


def get_layer_model(filled_img):
    """
    Generate a list of same velocity echo coordinate lists that have same length and according index
    value with the color velocity pairs
    :param filled_img: Pillow Image object of filled image
    :return: layer model
    """
    # Get dependency data
    radar_zone = utils.get_radar_info("radar_zone")
    cv_pairs = utils.get_color_bar_info("color_velocity_pairs")
    gray_value_interval = utils.gray_value_interval

    # Construct empty data structure
    layer_model = []
    for idx in range(len(cv_pairs)):
        layer_model.append([])

    # iterate the filled image
    for x in range(radar_zone[0], radar_zone[1]):
        for y in range(radar_zone[0], radar_zone[1]):
            # get current pixel value
            pixel_value = filled_img.getpixel((x, y))
            gray_index = round(pixel_value[0] * 1.0 / gray_value_interval) - 1

            if -1 < gray_index < len(cv_pairs):
                layer_model[gray_index].append((x, y))

    return layer_model

