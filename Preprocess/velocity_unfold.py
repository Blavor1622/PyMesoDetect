from PIL import Image, ImageDraw
import os
import time
import utils

unfold_result_folder = "unfold/"
unfold_layer_num = 3  # the num of layers from maximum absolute velocity value that might get folded
unfold_result_name = "unfolded.png"
unfold_debug_folder = "unfold_debug/"


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


def get_target_echoes(folder_path, filled_img, layer_model, gray_value_index):
    """
    Internal function for getting a list of enclosures of target echoes that might be folded
    which gray_value_index point to
    :param folder_path: path of result folder
    :param filled_img: a Pillow Image Object of filled image
    :param layer_model: the layer structure
    :param gray_value_index: the index of the pixel value in gray image
    :return: a list of enclosures of target echoes that might be folded
    """
    # Check valid gray_value_index
    if gray_value_index < 0 or gray_value_index > len(layer_model) - 1:
        print(f"[Error] Invalid gray_value_index: {gray_value_index} for `get_target_echoes`.")
        return

    # Get layer model half indexes range according to gray_value_index
    half_end_index = round(len(layer_model) / 2) - 1
    if gray_value_index <= half_end_index:
        half_range = range(half_end_index + 1, len(layer_model))
    else:
        half_range = range(0, half_end_index + 1)

    # Iterate layer model to draw merged image and get merged echo list
    radar_img_size = utils.get_radar_info("image_size")
    merged_img = Image.new("RGB", radar_img_size, (0, 0, 0))
    merged_draw = ImageDraw.Draw(merged_img)

    merge_debug_img = Image.new("RGB", radar_img_size, (0, 0, 0))
    merge_debug_draw = ImageDraw.Draw(merge_debug_img)

    merged_echo_list = []
    for layer_index in half_range:
        for coordinate in layer_model[layer_index]:
            merged_draw.point(coordinate, (255, 255, 255))
            merge_debug_draw.point(coordinate, (255, 255, 255))
            merged_echo_list.append(coordinate)

    # Draw echo that gray_value_index point to
    for coordinate in layer_model[gray_value_index]:
        merged_draw.point(coordinate, (255, 255, 255))
        merge_debug_draw.point(coordinate, (0, 255, 0))
        merged_echo_list.append(coordinate)

    # Get connected components of merged_echo_list
    merged_enclosure_list = get_connected_component(merged_img, merged_echo_list)

    # enclosure debug
    merged_enclosure_img = Image.new("RGB", radar_img_size, (0, 0, 0))
    merged_enclosure_draw = ImageDraw.Draw(merged_enclosure_img)
    for enclosure in merged_enclosure_list:
        for coordinate in enclosure:
            merged_enclosure_draw.point(coordinate, (0, 255, 0))

    # Get maximum enclosure among all enclosures in merged_enclosure_list
    maximum_len = 0
    maximum_index = 0
    for index in range(len(merged_enclosure_list)):
        if len(merged_enclosure_list[index]) > maximum_len:
            maximum_len = len(merged_enclosure_list[index])
            maximum_index = index

    maximum_merged_enclosure = merged_enclosure_list[maximum_index]

    # Debug maximum enclosure
    max_enclosure_img = Image.new("RGB", radar_img_size, (0, 0, 0))
    max_enclosure_draw = ImageDraw.Draw(max_enclosure_img)
    for coordinate in maximum_merged_enclosure:
        max_enclosure_draw.point(coordinate, (0, 255, 0))

    # Get enclosure list that gray_value_index point to
    might_folded_enclosures = get_connected_component(filled_img, layer_model[gray_value_index])

    # Iterate each enclosure in might_folded_enclosures to get target echoes
    target_echo_enclosures = []
    for enclosure in might_folded_enclosures:
        if enclosure[0] in maximum_merged_enclosure:
            target_echo_enclosures.append(enclosure)

    # Save debug images
    debug_num = str(gray_value_index)
    merge_debug_img.save(folder_path + unfold_result_folder + unfold_debug_folder + "merge_debug_" + debug_num + ".png")
    merged_enclosure_img.save(folder_path + unfold_result_folder + unfold_debug_folder + "merged_enclosures_" + debug_num + ".png")
    max_enclosure_img.save(folder_path + unfold_result_folder + unfold_debug_folder + "max_enclosure_" + debug_num + ".png")

    # Return list of target echo enclosure
    return target_echo_enclosures


def get_surrounding_echo_list(filled_img, enclosure):
    """
    get a list of echoes that is form an enclosure and return the surrounding echoes coordinate set
    :param filled_img: a Pillow Image Object of filled image
    :param enclosure: an enclosure of echoes
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

        # get self value for comparison
        self_value = filled_img.getpixel(echo_coordinate)
        self_index = round(self_value[0] * 1.0 / gray_value_interval) - 1

        # filter out inner echo
        if (surrounding_indexes[0] == surrounding_indexes[1]
                and surrounding_indexes[2] == surrounding_indexes[3]
                and surrounding_indexes[0] == surrounding_indexes[3]
                and surrounding_indexes[0] == self_index):
            continue

        # add not repeated surrounding echo coordinates
        for idx in range(len(surrounding_indexes)):
            if surrounding_indexes[idx] != self_index and surrounding_indexes[idx] > -1:
                surrounding_coordinate = (echo_coordinate[0] + surrounding_offsets[idx][0],
                                          echo_coordinate[1] + surrounding_offsets[idx][1])
                if surrounding_coordinate not in surrounding:
                    surrounding.add(surrounding_coordinate)

    return surrounding


def calculate_average_shear(filled_img, surrounding, instance_index):
    """
    this function calculate the average shear of a given surrounding echo list. The calculation
    does not include blank pixel
    :param filled_img: a Pillow Image Object of filled image
    :param surrounding: a set of surrounding echo coordinate
    :param instance_index: gray value index of echoes in target enclosure
    :return: the average shear value
    """
    if len(surrounding) == 0:
        return 0

    # Get color velocity pairs
    cv_pairs = utils.get_color_bar_info("color_velocity_pairs")
    gray_value_interval = utils.gray_value_interval

    enclosure_velocity = cv_pairs[instance_index][1]

    shear_sum = 0
    for coordinate in surrounding:
        # get current pixel color
        echo_color = filled_img.getpixel(coordinate)
        echo_index = round(1.0 * echo_color[0] / gray_value_interval) - 1
        echo_velocity = cv_pairs[echo_index][1]
        if echo_velocity >= enclosure_velocity:
            shear_sum += echo_velocity - enclosure_velocity
        else:
            shear_sum += enclosure_velocity - echo_velocity
    average_shear = shear_sum * 1.0 / len(surrounding)
    return average_shear


def replace_folded_echoes(folder_path, filled_img, unfolded_img, layer_model, target_index):
    """
    Internal function for detecting folded echoes and replace them
    with according maximum echo color
    :param folder_path: path of result folder
    :param filled_img: Pillow Image object of filled image
    :param unfolded_img: Pillow Image object for unfolding result image
    :param layer_model: a layers structure model that stores all echoes of filled image
    :param target_index: a gray value index, also valid index in color_velocity_pairs
    that points to target echo color
    :return: modified filled image
    """

    # Get replacement echo color
    gray_value_interval = utils.gray_value_interval
    half_index = round(len(layer_model) / 2) - 1
    if target_index <= half_index:
        replacement_index = len(layer_model) - 1
    else:
        replacement_index = 0
    replacement_value = (replacement_index + 1) * gray_value_interval
    replacement_color = (replacement_value, replacement_value, replacement_value)

    # Getting target folding echoes
    target_enclosures = get_target_echoes(folder_path, filled_img, layer_model, target_index)

    # Debug target enclosures
    target_enclosure_img = Image.new("RGB", filled_img.size, (0, 0, 0))
    target_enclosure_draw = ImageDraw.Draw(target_enclosure_img)

    # Debug surroundings
    surroundings_debug_img = Image.new("RGB", filled_img.size, (255, 255, 0))
    surroundings_debug_draw = ImageDraw.Draw(surroundings_debug_img)

    for target_enclosure in target_enclosures:
        for coordinate in target_enclosure:
            target_enclosure_draw.point(coordinate, (0, 255, 0))
            surroundings_debug_draw.point(coordinate, (0, 255, 0))

    # Create an unfolding image for batch iteration
    unfolded_draw = ImageDraw.Draw(unfolded_img)

    # Calculate average shear and threshold check for each target enclosure
    for target_enclosure in target_enclosures:
        # Get surrounding echo coordinates
        surrounding_echoes = get_surrounding_echo_list(filled_img, target_enclosure)

        for coordinate in surrounding_echoes:
            surroundings_debug_draw.point(coordinate, filled_img.getpixel(coordinate))

        # Calculate average shear of target enclosure
        avg_shear = calculate_average_shear(filled_img, surrounding_echoes, target_index)
        replaced_shear = calculate_average_shear(filled_img, surrounding_echoes, replacement_index)

        # Check with threshold
        if avg_shear > replaced_shear:
            for folded_echo in target_enclosure:
                unfolded_draw.point(folded_echo, replacement_color)
                surroundings_debug_draw.point(folded_echo, (255, 0, 0))

    # Save Debug image
    debug_num = str(target_index)
    target_enclosure_img.save(folder_path + unfold_result_folder + unfold_debug_folder + "target_enclosure_" + debug_num + ".png")
    surroundings_debug_img.save(folder_path + unfold_result_folder + unfold_debug_folder + "surroundings_" + debug_num + ".png")
    return unfolded_img


def unfold_doppler_velocity(folder_path, filled_img_path, batch_num):
    print("[Info] Start doppler velocity unfolding...")
    start = time.time()
    # Check result folder
    if not os.path.exists(folder_path + unfold_result_folder):
        os.makedirs(folder_path + unfold_result_folder)

    if not os.path.exists(folder_path + unfold_result_folder + unfold_debug_folder):
        os.makedirs(folder_path + unfold_result_folder + unfold_debug_folder)

    filled_img = Image.open(filled_img_path)

    # Iteration process of echo unfolding
    for unfold_batch in range(unfold_layer_num):
        # Get layer model
        layer_model = get_layer_model(filled_img)

        # Get indexes
        neg_layer_index = unfold_batch
        pos_layer_index = len(layer_model) - unfold_batch - 1

        # Check layer is empty or not
        if len(layer_model[neg_layer_index]) == 0 and len(layer_model[pos_layer_index]) == 0:
            print("[Info] Layer: " + str(neg_layer_index) + " and " + str(
                pos_layer_index) + " are empty, skipping analysis...")
            continue

        print('[Info] Start analysing layers: ' + str(neg_layer_index) + '(neg) and ' + str(pos_layer_index) + '(pos).')

        unfolded_img = filled_img.copy()
        unfolded_img = replace_folded_echoes(folder_path, filled_img, unfolded_img, layer_model, pos_layer_index)
        unfolded_img = replace_folded_echoes(folder_path, filled_img, unfolded_img, layer_model, neg_layer_index)
        filled_img = unfolded_img

    # Save unfolded result
    unfolded_result_path = folder_path + unfold_result_folder + str(batch_num) + "_" + unfold_result_name
    filled_img.save(unfolded_result_path)

    end = time.time()
    duration = end - start
    print(f"[Info] Duration of doppler velocity unfolding: {duration:.4f} seconds")
    return unfolded_result_path
