from PIL import Image, ImageDraw
import time
import os
import utils


denoise_folder_path = "denoise/"
debug_folder_path = denoise_folder_path + "debug/"


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


def get_layer_echo_groups(refer_img, coordinate_list, layer_index):
    """
    a utility function that divides the given coordinate_list
    and then return a list of connected components
    :param refer_img: a Pillow Image object that used for checking connected relationship of echoes
    :param coordinate_list: list of coordinate that might have several connected component
    :param layer_index: int value that indicate layer index which also equal to color value index
    :return: a list of connected components
    """
    # Check whether the input echoes list is empty or not
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
                        if round(neighbour_value * 1.0 / gray_value_interval) - 1 == layer_index:
                            # Mean that neighbour value similar to target value (slight difference is allowed)
                            if neighbour not in visited:
                                visited.add(neighbour)
                                component.append(neighbour)
                                stack.append(neighbour)

            components.append(component)
    return components


def layer_analysis(folder_path, narrow_filled_img_path):
    """

    :param folder_path:
    :param narrow_filled_img_path:
    :return:
    """
    start = time.time()
    print("[Info] Start denoise radar image...")
    # Check folder path
    analysis_result_folder = folder_path + denoise_folder_path
    if not os.path.exists(analysis_result_folder):
        os.makedirs(analysis_result_folder)
    analysis_debug_folder = folder_path + debug_folder_path
    if not os.path.exists(analysis_debug_folder):
        os.makedirs(analysis_debug_folder)

    # Get layer model
    filled_img = Image.open(narrow_filled_img_path)
    layer_model = get_layer_model(filled_img)

    # Create a Pillow image for drawing denoise result
    denoise_img = Image.new("RGB", filled_img.size, (0, 0, 0))
    denoise_draw = ImageDraw.Draw(denoise_img)

    cv_pairs = utils.get_color_bar_info("color_velocity_pairs")
    gray_value_interval = utils.gray_value_interval

    # Scan each layer of echoes
    for layer_idx in range(len(layer_model)):
        # Skip empty list
        if len(layer_model[layer_idx]) == 0:
            continue
        # Get connected echoes groups of current layer
        echo_enclosures = get_layer_echo_groups(filled_img, layer_model[layer_idx], layer_idx)
        # Draw debug image
        debug_img = Image.new("RGB", filled_img.size, (0, 0, 0))
        debug_draw = ImageDraw.Draw(debug_img)

        for enclosure in echo_enclosures:
            for echo_coordinate in enclosure:
                debug_draw.point(echo_coordinate, cv_pairs[layer_idx][0])

        debug_img.save(analysis_debug_folder + "layer_debug_" + str(layer_idx) + ".png")
    end = time.time()
    duration = end - start
    print(f"[Info] Duration of radar image denoise: {duration:.4f} seconds")
