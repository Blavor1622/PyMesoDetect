from PIL import Image, ImageDraw
import utils
import os
import time
from tqdm import tqdm


layer_analysis_folder = "layer_analysis/"


def get_layer_surroundings(filled_img, enclosure, current_layer_idx: int):
    """
    get a list of echoes that is form an enclosure and return the surrounding echoes coordinate set
    :param filled_img: a Pillow Image Object of filled image
    :param enclosure: an enclosure of echoes
    :param current_layer_idx: int value that indicate current layer index
    :return: a set of surrounding echoes
    """
    surrounding = set()
    # Return empty set for empty enclosure
    if len(enclosure) == 0:
        return surrounding

    # Get basic data
    gray_value_interval = utils.gray_value_interval
    surrounding_offsets = utils.surrounding_offsets

    # iterate echoes in enclosure
    for echo_coordinate in enclosure:
        # Get surrounding gray value index of current coordinate
        surrounding_indexes = []
        for offset in surrounding_offsets:
            neighbour_value = filled_img.getpixel((echo_coordinate[0] + offset[0],
                                                   echo_coordinate[1] + offset[1]))
            neighbour_index = round(1.0 * neighbour_value[0] / gray_value_interval) - 1
            surrounding_indexes.append(neighbour_index)

        # filter out inner echo
        if (surrounding_indexes[0] == surrounding_indexes[1]
                and surrounding_indexes[2] == surrounding_indexes[3]
                and surrounding_indexes[0] == surrounding_indexes[3]
                and surrounding_indexes[0] == current_layer_idx):
            continue

        # add not repeated surrounding echo coordinates
        for idx in range(len(surrounding_indexes)):
            if surrounding_indexes[idx] != current_layer_idx:
                surrounding_coordinate = (echo_coordinate[0] + surrounding_offsets[idx][0],
                                          echo_coordinate[1] + surrounding_offsets[idx][1])
                if surrounding_coordinate not in surrounding:
                    surrounding.add((surrounding_coordinate, surrounding_indexes[idx]))

    return surrounding


def get_layer_model(filled_img):
    """
    this function analyze filled image and return a soak struction
    :param filled_img: Pillow Image object of filled image
    :return: a layer struction that divides the filled image with same value echo in a layer
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


def get_connected_component(refer_img, coordinate_list):
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
    neighbour_offsets = [(0, -1), (0, 1), (-1, 0), (1, 0)]

    # Get radar zone
    radar_zone = utils.get_radar_info("radar_zone")
    gray_value_interval = utils.gray_value_interval

    components = []
    visited = set()
    for point in coordinate_list:
        if point not in visited:
            visited.add(point)
            stack = [point]
            component = [point]

            # Extract gray value index of current point
            target_value = refer_img.getpixel(point)[0]
            target_index = round(1.0 * target_value / gray_value_interval) - 1

            while stack:
                current_point = stack.pop()
                neighbours = []

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
                            neighbours.append(neighbour)

                for neighbour in neighbours:
                    if neighbour not in visited:
                        visited.add(neighbour)
                        component.append(neighbour)
                        stack.append(neighbour)

            components.append(component)
    return components


def echo_surroundings_analysis_v1(echo_enclosure, surroundings, layer_index, half_index, mode):
    """
    Analise surrounding echo of given echo enclosure to judge whether to actually fill
    the place that enclosure taken with which color index
    Args:
        echo_enclosure: a list of connected same value echo coordinates
        surroundings: a list of echo coordinates that surround the given enclosure
        layer_index: color index of the given enclosure
        half_index: half of the color_velocity_pairs index
        mode: a string which indicate the velocity sign of given enclosure and value only in "neg" and "pos"

    Returns: A int which value indicate the color that can fill for given enclosure.
            Returns -1 if there is no need for filling.

    """
    # If enclosure size is huge, then it is possible real
    if len(echo_enclosure) >= 36:
        return layer_index

    # Get same sign surrounding set
    same_sign_surroundings = []
    # half_vale_indexes = []
    for surrounding in surroundings:
        if mode == "neg" and layer_index < surrounding[1] < half_index + 1:
            same_sign_surroundings.append(surrounding)
        elif mode == "pos" and half_index < surrounding[1] < layer_index:
            same_sign_surroundings.append(surrounding)

    # If enclosure is an isolated enclosure then return -1 for not filling
    if len(same_sign_surroundings) == 0:
        return -1
    else:
        return layer_index


def layer_analysis(folder_path, filled_img_path):
    start = time.time()
    print("[Info] Start layer analysis...")
    # Check result folder path
    analysis_result_folder = folder_path + layer_analysis_folder
    if not os.path.exists(analysis_result_folder):
        os.makedirs(analysis_result_folder)

    # Check layer debug folder path
    layer_debug_folder = folder_path + layer_analysis_folder + "layer_debug/"
    if not os.path.exists(layer_debug_folder):
        os.makedirs(layer_debug_folder)

    layer_fill_folder = folder_path + layer_analysis_folder + "layer_fill/"
    if not os.path.exists(layer_fill_folder):
        os.makedirs(layer_fill_folder)

    # Get layer model
    filled_img = Image.open(filled_img_path)
    layer_model = get_layer_model(filled_img)

    # Create a Pillow Image as layer image
    neg_layer_img = Image.new("RGB", filled_img.size, (0, 0, 0))
    neg_layer_draw = ImageDraw.Draw(neg_layer_img)

    cv_pairs = utils.get_color_bar_info("color_velocity_pairs")
    gray_value_interval = utils.gray_value_interval
    half_index = round(len(layer_model) / 2) - 1
    # Start layer analysis in same velocity sign (positive and negative)
    # A) Negative analysis
    # Initialize layer image
    half_gray_value = (half_index + 1) * gray_value_interval
    for layer_idx in range(0, half_index + 1):
        for echo_coordinate in layer_model[layer_idx]:
            # Use minimum velocity value to initialize the layer image
            neg_layer_draw.point(echo_coordinate, (half_gray_value, half_gray_value, half_gray_value))

    # Save initialization image for debugging
    neg_layer_img.save(analysis_result_folder + "ini_neg.png")

    # Skip the first layer and start analysis
    for layer_idx in range(half_index - 1, -1, -1):
        # Get current layer echoes enclosures
        layer_echo_enclosures = get_connected_component(filled_img, layer_model[layer_idx])

        # Debug image for each layer
        debug_img = Image.new("RGB", filled_img.size, (0, 0, 0))
        debug_draw = ImageDraw.Draw(debug_img)

        # Start analysis each enclosure
        current_iterations = len(layer_echo_enclosures)
        with tqdm(total=current_iterations, desc="  Layer Analysis Progress", unit="enclosures") as pbar:
            for echo_enclosure in layer_echo_enclosures:
                # Get surroundings of each enclosure
                surroundings = get_layer_surroundings(neg_layer_img, echo_enclosure, layer_idx)

                # Draw surroundings for each enclosure
                for surrounding in surroundings:
                    if surrounding[1] != -1:
                        debug_draw.point(surrounding[0], cv_pairs[surrounding[1]][0])

                value_index = echo_surroundings_analysis_v1(echo_enclosure, surroundings, layer_idx, half_index, "neg")

                if value_index != -1:
                    gray_value = (value_index + 1) * gray_value_interval
                    for coordinate in echo_enclosure:
                        neg_layer_draw.point(coordinate, (gray_value, gray_value, gray_value))
                        debug_draw.point(coordinate, cv_pairs[value_index][0])

                pbar.update(1)

        # Save layer debug image
        debug_img.save(layer_debug_folder + "surroundings_" + str(layer_idx) + ".png")

        neg_layer_img.save(layer_fill_folder + "filled_" + str(layer_idx) + ".png")

    # Save result image
    layer_merge_path = analysis_result_folder + "layer_merge.png"

    end = time.time()
    duration = end - start
    print(f"[Info] Duration of layer analysis: {duration:.4f} seconds")
    return layer_merge_path