from PIL import Image, ImageDraw
import os
import time
import utils


def get_echo_list(img_path, target_color):
    """
    this is a dependency function which take a path of image and then return a list of coordinate
    whose color match the target_color
    :param img_path: the path of radar image or internal image
    :param target_color: rgb color that used for matching
    :return: a list of coordinate
    """
    # open the image
    img = Image.open(img_path)

    # Get dependency data
    radar_zone = utils.get_radar_info("radar_zone")

    coordinates = []
    # iterate pixel within radar area
    for x in range(radar_zone[0], radar_zone[1]):
        for y in range(radar_zone[0], radar_zone[1]):
            # get pixel value
            pixel_value = img.getpixel((x, y))

            # check whether is echo or not
            if utils.is_color_equal(pixel_value, target_color, 10):
                coordinates.append((x, y))

    # return the coordinate list
    return coordinates


def get_connected_component(refer_image_path, coordinate_list, is_strict):
    """
    a utility function that divides the given coordinate_list
    and then return a list of connected components
    :param refer_image_path: path of image that describes the relationship of pixels
    :param coordinate_list: list of coordinate that might have several connected component
    :param is_strict: a boolean value that indicates whether the neighbour relationship check is strict or not
    :return: a list of connected components
    """
    # get neighbour coordinate offset according to the flag
    if is_strict:
        neighbour_offsets = [(0, -1), (0, 1), (-1, 0), (1, 0)]
    else:
        neighbour_offsets = [(0, -1), (0, 1), (-1, 0), (1, 0),
                                 (-1, -1), (1, -1), (-1, 1), (1, 1)]

    # open the refer image
    refer_image = Image.open(refer_image_path)

    # Get radar zone
    radar_zone = utils.get_radar_info("radar_zone")

    target_color = refer_image.getpixel(coordinate_list[0])
    components = []
    visited = set()
    for point in coordinate_list:
        if point not in visited:
            visited.add(point)
            stack = [point]
            component = [point]

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
                        neighbour_value = refer_image.getpixel(neighbour)
                        if utils.is_color_equal(neighbour_value, target_color, 10):
                            neighbours.append(neighbour)

                for neighbour in neighbours:
                    if neighbour not in visited:
                        visited.add(neighbour)
                        component.append(neighbour)
                        stack.append(neighbour)

            components.append(component)
    return components


def get_layer_model(filled_img_path):
    """
    this function analyze filled image and return a soak struction
    :param filled_img_path: path of filled image
    :return: a layer struction that describe the filled image using soaking model
    """
    start = time.time()
    print(f'  2.1: start getting layer model...')
    # Get dependency data
    radar_zone = utils.get_radar_info("radar_zone")
    neg_color_scales = utils.get_half_color_bar("neg")
    pos_color_scales = utils.get_half_color_bar("pos")

    # open filled image
    filled_img = Image.open(filled_img_path)

    # data structures
    neg_frames = [[], [], [], [], [], [], []]
    pos_frames = [[], [], [], [], [], [], []]

    # iterate the filled image
    for x in range(radar_zone[0], radar_zone[1]):
        for y in range(radar_zone[0], radar_zone[1]):
            # get current pixel value
            pixel_value = filled_img.getpixel((x, y))

            is_match = False
            # iterate the negative color scale first for matching
            for scale_index in range(len(neg_color_scales)):
                if utils.is_color_equal(pixel_value, neg_color_scales[scale_index], 10):
                    neg_frames[scale_index].append((x, y))
                    is_match = True
                    break

            if is_match:
                continue
            # positive color scale matching
            for scale_index in range(len(pos_color_scales)):
                if utils.is_color_equal(pixel_value, pos_color_scales[scale_index], 10):
                    pos_frames[scale_index].append((x, y))
                    break

    end = time.time()
    duration = end - start
    print('  2.1: generation of layer model complete!')
    print(f'  2.1: duration of getting layer model: {duration:.4f} seconds')
    return [neg_frames, pos_frames]


def get_merged_img(folder_path, layer_model, scale_index):
    """
    this function generate an image that merge one half of velocity echoes
    and echo that scale_index points to for latter removing blur analysis
    :param folder_path: path of current process result folder
    :param layer_model: a list of echo frame
    :param scale_index: the index that reference to color_velocity_pairs in consts.py item
    means echo that need further blur analysis
    :return: the path of merged image with format: '/blur/merged_image+scale_index+.png'
    """
    # Get basic data
    cv_pairs = utils.get_color_bar_info("color_velocity_pairs")
    radar_img_size = utils.get_radar_info("image_size")

    # check result path
    if not os.path.exists(folder_path + '/blur'):
        os.makedirs(folder_path + '/blur')

    # check scale_index
    if scale_index < 0 or scale_index >= len(cv_pairs):
        print(f'\033[91m[error]Invalid scale_index = {scale_index} for `get_merged_img`.\033[0m')
        return

    # analyse the scale_index
    if scale_index >= 7:
        half_index = 0
        blur_index = scale_index - 7
    else:
        half_index = 1
        blur_index = 6 - scale_index

    # generate merged image
    merged_img = Image.new("RGB", radar_img_size, (0, 0, 0))
    merged_draw = ImageDraw.Draw(merged_img)

    # first draw whole half velocity echoes
    for frame in layer_model[half_index]:
        for coordinate in frame:
            # all draw with green color
            merged_draw.point(coordinate, (0, 255, 0))

    # draw echo that scale_index points to
    for coordinate in layer_model[1 - half_index][blur_index]:
        merged_draw.point(coordinate, (0, 255, 0))

    # save merged image
    result_path = folder_path + '/blur/merged_image' + str(scale_index) + '.png'
    merged_img.save(result_path)
    return result_path


def get_max_component_img(folder_path, components, scale_index):
    """
    Generating an image that have the biggest component
    :param folder_path: path of result folder
    :param components: a list of connected component
    :param scale_index: index that acts as a flat for distinguishing different analysis
    :return: path of result image
    """
    # check result path
    if not os.path.exists(folder_path + '/blur'):
        os.makedirs(folder_path + '/blur')

    # get the biggest component
    max_len = 0
    max_index = 0
    for idx in range(len(components)):
        if len(components[idx]) > max_len:
            max_len = len(components[idx])
            max_index = idx

    # Get radar image size
    img_size = utils.get_radar_info("image_size")

    # draw the biggest component
    img = Image.new("RGB", img_size, (0, 0, 0))
    img_draw = ImageDraw.Draw(img)

    for coordinate in components[max_index]:
        img_draw.point(coordinate, (0, 255, 0))

    # save result image
    result_path = folder_path + '/blur/max_com' + str(scale_index) + '.png'
    img.save(result_path)
    return result_path


def get_blur_including_component(folder_path, filled_img_path, layer_model, biggest_component, scale_index):
    """
    Getting list of component that might include blur echoes which scale_index points to
    :param folder_path: path of result folder
    :param filled_img_path: path of filled image
    :param layer_model: a list of frames that have same color echoes at same layer
    :param biggest_component: a list of biggest component coordinate
    :param scale_index: the index that point to item of color_velocity_pair in consts.py
    :return: a list of component that might have blur echoes
    """
    # Get basic data
    cv_pairs = utils.get_color_bar_info("color_velocity_pairs")
    image_size = utils.get_radar_info("image_size")

    # check result path
    if not os.path.exists(folder_path + '/blur'):
        os.makedirs(folder_path + '/blur')

    # check scale_index
    if scale_index < 0 or scale_index >= len(cv_pairs):
        print(f'\033[91m[error]Invalid scale_index = {scale_index} for `get_blur_including_component`.\033[0m')
        return

    # analyse the scale_index
    if scale_index >= 7:
        half_index = 1
        blur_index = scale_index - 7
    else:
        half_index = 0
        blur_index = 6 - scale_index

    # get target echoes enclosures
    target_echo_components = get_connected_component(filled_img_path,
                                                     layer_model[half_index][blur_index], True)

    # get merged target echoes enclosures
    merged_target_echo_components = []
    for component in target_echo_components:
        if component[0] in biggest_component:
            merged_target_echo_components.append(component)

    # filter result visualization
    test_img = Image.new("RGB", image_size, (0, 0, 0))
    test_draw = ImageDraw.Draw(test_img)

    for component in merged_target_echo_components:
        for coordinate in component:
            test_draw.point(coordinate, cv_pairs[scale_index][0])

    # save test result
    result_path = folder_path + '/blur/merged_targets' + str(scale_index) + '.png'
    test_img.save(result_path)

    # return the filtered result that might contain blur echoes
    return merged_target_echo_components


def get_merged_target_echoes(folder_path, filled_img_path, layer_model, scale_index):
    """
    for outer scope calling to get a list of connected component of merged target echoes
    :param folder_path: path of test result folder
    :param filled_img_path: path of filled image
    :param layer_model: a list of frames that composes layers of same color scale echo
    :param scale_index: index that points to item in color_velocity_pair in consts.py
    :return: a list of connected component in which contains all echo coordinate within the component
    """
    start = time.time()
    print(f'  2.2: start getting merged target echoes for scale_index = {scale_index}...')
    # get merged image
    merged_img_path = get_merged_img(folder_path, layer_model, scale_index)

    # get echo list from merged image
    echo_list = get_echo_list(merged_img_path, (0, 255, 0))

    # get connected components from merged image
    components = get_connected_component(merged_img_path, echo_list, True)

    # draw the biggest component
    biggest_component_img_path = get_max_component_img(folder_path, components, scale_index)

    # get the biggest component list
    biggest_component_list = get_echo_list(biggest_component_img_path, (0, 255, 0))

    # get filtered target components
    target_components = get_blur_including_component(folder_path, filled_img_path, layer_model, biggest_component_list, scale_index)

    end = time.time()
    duration = end - start
    print('  2.2: getting merged target echoes complete!')
    print(f'  2.2: duration of getting merged target echoes: {duration:.4f} seconds')
    return target_components


def get_surrounding_echo_list(filled_img_path, enclosure):
    """
    get a list of echoes that is form an enclosure and return the surrounding echoes coordinate set
    :param filled_img_path: path of filled image
    :param enclosure: an enclosure of echoes
    :return: a set of surrounding echoes
    """
    # open the filled image
    filled_img = Image.open(filled_img_path)

    surrounding = set()
    # iterate echoes in enclosure
    for echo_coordinate in enclosure:
        # get pixel value around the current echo
        top_coordinate = (echo_coordinate[0], echo_coordinate[1] - 1)
        top_value = filled_img.getpixel(top_coordinate)
        bottom_coordinate = (echo_coordinate[0], echo_coordinate[1] + 1)
        bottom_value = filled_img.getpixel(bottom_coordinate)
        left_coordinate = (echo_coordinate[0] - 1, echo_coordinate[1])
        left_value = filled_img.getpixel(left_coordinate)
        right_coordinate = (echo_coordinate[0] + 1, echo_coordinate[1])
        right_value = filled_img.getpixel(right_coordinate)

        # filter out inner echo
        if (utils.is_color_equal(top_value, bottom_value, 10)
                and utils.is_color_equal(left_value, right_value, 10)
                and utils.is_color_equal(top_value, right_value, 10)):
            continue

        # get self value for comparison
        self_value = filled_img.getpixel(echo_coordinate)

        # add not repeated surrounding echo coordinates
        if (not utils.is_color_equal(top_value, self_value, 10)
                and not utils.is_color_equal(top_value, (0, 0, 0), 10)):
            if top_coordinate not in surrounding:
                surrounding.add(top_coordinate)
        if (not utils.is_color_equal(bottom_value, self_value, 10)
                and not utils.is_color_equal(bottom_value, (0, 0, 0), 10)):
            if bottom_coordinate not in surrounding:
                surrounding.add(bottom_coordinate)
        if (not utils.is_color_equal(left_value, self_value, 10)
                and not utils.is_color_equal(left_value, (0, 0, 0), 10)):
            if left_coordinate not in surrounding:
                surrounding.add(left_coordinate)
        if (not utils.is_color_equal(right_value, self_value, 10)
                and not utils.is_color_equal(right_value, (0, 0, 0), 10)):
            if right_coordinate not in surrounding:
                surrounding.add(right_coordinate)

    return surrounding


def calculate_average_shear(filled_img_path, surrounding, enclosure_instance):
    """
    this function calculate the average shear of a given surrounding echo list. The calculation
    does not include blank pixel
    :param filled_img_path: path of filled image
    :param surrounding: a set of surrounding echo coordinate
    :param enclosure_instance: one coordinate instance in the enclosure that the surrounding set surrounds with
    :return: the average shear value
    """
    if len(surrounding) == 0:
        return 0

    # Get color velocity pairs
    cv_pairs = utils.get_color_bar_info("color_velocity_pairs")

    # open the filled image of sale color matching
    filled_img = Image.open(filled_img_path)

    # get the velocity value of current enclosure
    instance_color = filled_img.getpixel(enclosure_instance)
    enclosure_velocity = 0
    for c_v_pair in cv_pairs:
        if utils.is_color_equal(instance_color, c_v_pair[0], 10):
            enclosure_velocity = c_v_pair[1]
            break

    shear_sum = 0
    for coordinate in surrounding:
        # get current pixel color
        echo_color = filled_img.getpixel(coordinate)

        for c_v_pair in cv_pairs:
            if utils.is_color_equal(echo_color, c_v_pair[0], 10):
                current_velocity = c_v_pair[1]
                if current_velocity >= enclosure_velocity:
                    shear_sum += current_velocity - enclosure_velocity
                else:
                    shear_sum += enclosure_velocity - current_velocity
                break

    average_shear = shear_sum * 1.0 / len(surrounding)
    return average_shear


def replace_blur_echo(filled_img_path, target_components, rm_img, filled_img, mode):
    """
    Dependency function for detect target echo group and replace it with according scale color
    :param filled_img_path: path of filled image
    :param target_components: a list of connected component that contains same scale echoes
    :param rm_img: an Image for visualization of echoes that are replaced during this function call
    :param filled_img: a final result Image of velocity blur removing process
    :param mode: a string that indicate the intended velocity for replacement which is reversed with
    the target_components
    :return: none
    """
    start = time.time()
    print(f'  2.3: start replacing blur echoes for mode = {mode}...')
    # first check mode code
    if mode != 'neg' and mode != 'pos':
        print(f'\033[91m[error]Invalid mode code = {mode} for `replace_blur_echo`.\033[0m')
        return

    # Get basic data
    blur_threshold = utils.get_threshold("blur_threshold")
    neg_color_scales = utils.get_half_color_bar("neg")
    pos_color_scales = utils.get_half_color_bar("pos")

    # create drawer for the image
    rm_draw = ImageDraw.Draw(rm_img)
    filled_draw = ImageDraw.Draw(filled_img)

    # iterate each enclosure for velocity check
    for enclosure in target_components:
        # get surrounding of current enclosure
        surrounding = get_surrounding_echo_list(filled_img_path, enclosure)

        # calculate the shear of the component
        average_shear = calculate_average_shear(filled_img_path, surrounding, enclosure[0])

        # check with shear threshold
        if average_shear >= blur_threshold:
            # iterate each echo within the enclosure
            for coordinate in enclosure:
                if mode == 'neg':
                    rm_draw.point(coordinate, neg_color_scales[6])
                    filled_draw.point(coordinate, neg_color_scales[6])
                else:
                    rm_draw.point(coordinate, pos_color_scales[6])
                    filled_draw.point(coordinate, pos_color_scales[6])

    end = time.time()
    duration = end - start
    print('  2.3: replacing blur echoes complete!')
    print(f'  2.3: duration of replacing blur echoes: {duration:.4f} seconds')


def remove_velocity_blur(folder_path, filled_img_path):
    print('--------------------')
    print('[2] start velocity blur removing process...')
    start = time.time()
    # get layer model
    layer_model = get_layer_model(filled_img_path)

    # get target echoes
    neg_targets = get_merged_target_echoes(folder_path, filled_img_path, layer_model, 1)
    pos_targets = get_merged_target_echoes(folder_path, filled_img_path, layer_model, 12)

    # Get image size
    image_size = utils.get_radar_info("image_size")

    # create result image
    rm_img = Image.new("RGB", image_size, (0, 0, 0))
    filled_img = Image.open(filled_img_path)

    # for neg mode
    replace_blur_echo(filled_img_path, pos_targets, rm_img, filled_img, 'neg')

    # for pos mode
    replace_blur_echo(filled_img_path, neg_targets, rm_img, filled_img, 'pos')

    # save the result image
    rm_img.save(folder_path + '/blur/remove.png')
    rm_filled_img_path = folder_path + '/blur/rm_filled.png'
    filled_img.save(rm_filled_img_path)

    print('[2] velocity blur removing process complete!')
    end = time.time()
    duration = end - start
    print(f'[2] duration of velocity blur removing process: {duration:.4f} seconds')

    return rm_filled_img_path
