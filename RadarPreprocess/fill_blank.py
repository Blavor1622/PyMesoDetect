import math
import time
from PIL import Image, ImageDraw
from RadarPreprocess import consts
import os
from tqdm import tqdm


def get_neighbour_component_size(refer_image, neighbour_coordinate, is_strict):
    """
    get the size of the connected component that a given neighbour belong to
    :param refer_image: a PIL image object describes the adjacent relationship of given pixel
    :param neighbour_coordinate: the coordinate of neighbour, which is used for getting the target color
    :param is_strict: a boolean value that indicates whether the neighbour relationship check is strict or not
    :return: an int vlue that refer to the size of connected component
    """
    # get neighbour coordinate offset according to the flag
    if is_strict:
        neighbour_offsets = consts.surrounding_offsets
    else:
        neighbour_offsets = [(0, -1), (0, 1), (-1, 0), (1, 0),
                             (-1, -1), (1, -1), (-1, 1), (1, 1)]

    # get target color of the given neighbour
    target_color = refer_image.getpixel(neighbour_coordinate)

    # check whether is blank or not
    if consts.is_color_equal(target_color, (0, 0, 0), 10):
        return 0

    # get connected component that neighbour belongs to
    visited = set()
    visited.add(neighbour_coordinate)
    stack = [neighbour_coordinate]
    component = [neighbour_coordinate]

    while stack:
        # threshold check for acceleration
        if len(component) >= consts.narrow_fill_threshold:
            break
        current_point = stack.pop()
        neighbours = []

        # get surrounding pixel values
        for offset in neighbour_offsets:
            # ger neighbour pixel coordinate
            neighbour = (current_point[0] + offset[0], current_point[1] + offset[1])
            # radar scale check
            if (consts.radar_area[0] <= neighbour[0] <= consts.radar_area[1]
                    and consts.radar_area[0] <= neighbour[1] <= consts.radar_area[1]):
                neighbour_value = refer_image.getpixel(neighbour)
                if consts.is_color_equal(neighbour_value, target_color, 10):
                    neighbours.append(neighbour)

        for neighbour in neighbours:
            if neighbour not in visited:
                visited.add(neighbour)
                component.append(neighbour)
                stack.append(neighbour)

    return len(component)


def get_complex_fill_color(radar_img, current_coordinate, surrounding_values):
    """
    A dependency function for getting the color that for current coordinate by using complex filling
    :param radar_img: a PIL image object that is used for getting the connected component size of neighbour echo
    :param current_coordinate: the coordinate of current blank pixel that need complex filling
    :param surrounding_values: list of surrounding neighbour pixel values
    :return: an echo value for filling
    """
    # get surrounding enclosure size
    surrounding_sizes = [0, 0, 0, 0]
    for idx in range(len(surrounding_values)):
        # filter out blank neighbour pixel
        if consts.is_color_equal(surrounding_values[idx], (0, 0, 0), 10):
            continue

        # get size enclosure for surrounding echo
        surrounding_sizes[idx] = get_neighbour_component_size(radar_img,
                                                             (current_coordinate[0] + consts.surrounding_offsets[idx][0],
                                                              current_coordinate[1] + consts.surrounding_offsets[idx][1]), True)
        # process accelerate
        if surrounding_sizes[idx] >= consts.narrow_fill_threshold:
            return surrounding_values[idx]

    # iterate the surrounding enclosure size to get maximum size neighbour
    max_len = 0
    max_len_idx = 0
    for idx in range(len(surrounding_sizes)):
        if surrounding_sizes[idx] > max_len:
            max_len = surrounding_sizes[idx]
            max_len_idx = idx

    return surrounding_values[max_len_idx]


def narrow_fill(folder_path, radar_read_path):
    """
    Filling narrow blank area in radar image that covered radar image mark.
    Use maximum neighbour enclosure for filling when the neighbors around blank
    not match the "narrow condition"
    :param folder_path: path of test result folder
    :param radar_read_path: path of radar read result image
    :return: path of process result image
    """
    start = time.time()
    print(f'  1.1: start narrow filling...')
    # check result folder path
    if not os.path.exists(folder_path + '/fill_blank'):
        os.makedirs(folder_path + '/fill_blank')

    # first open the read result image
    radar_img = Image.open(radar_read_path)
    fill_img = Image.open(radar_read_path)
    fill_draw = ImageDraw.Draw(fill_img)

    # debug image
    debug_img = Image.open(consts.v_base_path)
    debug_draw = ImageDraw.Draw(debug_img)

    total_iterations = (consts.radar_area[1] - consts.radar_area[0]) ** 2
    with tqdm(total=total_iterations, desc="  Filling Progress", unit="pixels") as pbar:
        for x in range(consts.radar_area[0], consts.radar_area[1]):
            for y in range(consts.radar_area[0], consts.radar_area[1]):
                # get current pixel value
                pixel_value = radar_img.getpixel((x, y))

                # filter our not blank pixel
                if not consts.is_color_equal(pixel_value, (0, 0, 0), 10):
                    pbar.update(1)
                    continue

                # get surrounding pixel value
                surroundings_value = []
                for offset in consts.surrounding_offsets:
                    neighbour_value = radar_img.getpixel((x + offset[0], y + offset[1]))
                    surroundings_value.append(neighbour_value)

                # filter out pixels that does not have side fill condition (at least both side have echoes)
                if not ((not consts.is_color_equal(surroundings_value[0], (0, 0, 0), 10)
                         and not consts.is_color_equal(surroundings_value[1], (0, 0, 0), 10))
                        or not consts.is_color_equal(surroundings_value[2], (0, 0, 0), 10)
                        and not consts.is_color_equal(surroundings_value[3], (0, 0, 0), 10)):
                    pbar.update(1)
                    continue

                # check opposite side pixel value for filling
                if (consts.is_color_equal(surroundings_value[0], surroundings_value[1], 10)
                        and not consts.is_color_equal(surroundings_value[0], (0, 0, 0), 10)
                        and consts.is_color_equal(surroundings_value[2], surroundings_value[3], 10)
                        and consts.is_color_equal(surroundings_value[2], (0, 0, 0), 10)):
                    fill_draw.point((x, y), surroundings_value[0])
                    debug_draw.point((x, y), surroundings_value[0])
                    pbar.update(1)
                    continue

                if (consts.is_color_equal(surroundings_value[2], surroundings_value[3], 10)
                        and not consts.is_color_equal(surroundings_value[2], (0, 0, 0), 10)
                        and consts.is_color_equal(surroundings_value[0], surroundings_value[1], 10)
                        and consts.is_color_equal(surroundings_value[0], (0, 0, 0), 10)):
                    fill_draw.point((x, y), surroundings_value[2])
                    debug_draw.point((x, y), surroundings_value[2])
                    pbar.update(1)
                    continue

                # get surrounding color index
                surrounding_index = []
                for value in surroundings_value:
                    # remove blank pixel
                    if consts.is_color_equal(value, (0, 0, 0), 10):
                        continue

                    # iterate the color scale to get index
                    for idx in range(len(consts.color_velocity_pairs)):
                        if consts.is_color_equal(value, consts.color_velocity_pairs[idx][0], 10):
                            surrounding_index.append(idx)
                            break

                # check whether to execute complex fill or not
                if max(surrounding_index) - min(surrounding_index) < consts.complex_fill_check_threshold:
                    average_index = sum(surrounding_index) * 1.0 / len(surrounding_index)
                    fill_draw.point((x, y), consts.color_velocity_pairs[math.floor(average_index)][0])
                    debug_draw.point((x, y), consts.color_velocity_pairs[math.floor(average_index)][0])
                    pbar.update(1)
                    continue

                complex_filled_value = get_complex_fill_color(radar_img, (x, y), surroundings_value)

                # fill blank
                fill_draw.point((x, y), complex_filled_value)
                debug_draw.point((x, y), complex_filled_value)
                pbar.update(1)

    # save test image
    filled_img_path = folder_path + '/fill_blank/narrow_filled.png'
    fill_img.save(filled_img_path)

    # save debug image
    debug_img.save(folder_path + '/fill_blank/narrow_debug.png')

    end = time.time()
    duration = end - start
    print('  1.1: narrow filling complete!')
    print(f'  1.1: duration of narrow filling: {duration:.4f} seconds')
    return filled_img_path


def get_color_index(pixel_value):
    """
    a dependency function that read a rgb color value
    and then return the index in color_velocity_pair of consts.py or -1 if value is not matched
    :param pixel_value: rgb color value
    :return: int value
    """
    if consts.is_color_equal(pixel_value, (0, 0, 0), 10):
        return -1

    for idx in range(len(consts.color_velocity_pairs)):
        if consts.is_color_equal(pixel_value, consts.color_velocity_pairs[idx][0], 10):
            return idx

    return -1


def get_blank_list(folder_path, fill_img):
    """
    this function iterate the original filled image and return a list of blank pixels in it
    :param folder_path: a given folder for one radar scanning
    :param fill_img: the Image object of original filled image
    :return: list of blank pixels of original filled image
    """

    # iterate the radar image to get a list of blank pixel
    blank_list = []
    for x in range(consts.radar_area[0], consts.radar_area[1]):
        for y in range(consts.radar_area[0], consts.radar_area[1]):
            if math.sqrt(
                    (x - consts.radar_center[0]) ** 2 + (y - consts.radar_center[1]) ** 2) >= consts.radar_diameter - 1:
                continue
            # get current pixel value
            pixel = fill_img.getpixel((x, y))

            if consts.is_color_equal(pixel, (0, 0, 0), 10):
                blank_list.append((x, y))

    # draw the blanks and generate a debug image
    img = Image.open(consts.v_base_path)
    draw = ImageDraw.Draw(img)
    for coordinate in blank_list:
        draw.point(coordinate, (255, 0, 255))

    img.save(folder_path + '/fill_blank/whole_blanks.png')

    return blank_list


def get_blank_enclosure(fill_img, blank_list):
    """
    this function iterates the list of blank pixels list and groups them into enclosures
    in which pixels are next to each other
    :param fill_img: the original filled image
    :param blank_list: list of blank pixels
    :return: list of enclosure of blank pixels
    """
    # iterate the blank list
    blank_contours = []
    visited = set()
    for coordinate in blank_list:
        if coordinate not in visited:
            contour = [coordinate]
            visited.add(coordinate)
            stack = [coordinate]

            while stack:
                current_pixel = stack.pop()

                # get surrounding pixel values
                top_pixel = (current_pixel[0], current_pixel[1] - 1)
                top_pixel_value = fill_img.getpixel(top_pixel)

                bottom_pixel = (current_pixel[0], current_pixel[1] + 1)
                bottom_pixel_value = fill_img.getpixel(bottom_pixel)

                left_pixel = (current_pixel[0] - 1, current_pixel[1])
                left_pixel_value = fill_img.getpixel(left_pixel)

                right_pixel = (current_pixel[0] + 1, current_pixel[1])
                right_pixel_value = fill_img.getpixel(right_pixel)

                adjacent_pixels = []
                if consts.is_color_equal(top_pixel_value, (0, 0, 0), 10):
                    adjacent_pixels.append(top_pixel)

                if consts.is_color_equal(bottom_pixel_value, (0, 0, 0), 10):
                    adjacent_pixels.append(bottom_pixel)

                if consts.is_color_equal(left_pixel_value, (0, 0, 0), 10):
                    adjacent_pixels.append(left_pixel)

                if consts.is_color_equal(right_pixel_value, (0, 0, 0), 10):
                    adjacent_pixels.append(right_pixel)

                # iterate all neighbours
                for neighbour in adjacent_pixels:
                    # note that the neighbour pixel might out of radar range
                    if (not consts.radar_area[0] <= neighbour[0] <= consts.radar_area[1]
                            or not consts.radar_area[0] <= neighbour[1] <= consts.radar_area[1]):
                        continue
                    if neighbour not in visited:
                        visited.add(neighbour)
                        contour.append(neighbour)
                        stack.append(neighbour)
            blank_contours.append(contour)

    return blank_contours


def fill_blank_enclosure(folder_path, fill_img, blank_contours):
    """
    this function fill the blank enclosure that has been filtered
    :param folder_path: given path of a radar scan test
    :param fill_img: original filled image
    :param blank_contours: list of enclosure of blank pixels
    """
    # filter blank contour
    filtered_contours = []
    for contour in blank_contours:
        if len(contour) <= consts.area_need_filled_threshold:
            filtered_contours.append(contour)

    test_img = Image.open(consts.v_base_path)
    test_draw = ImageDraw.Draw(test_img)

    for contour in filtered_contours:
        for coordinate in contour:
            test_draw.point(coordinate, (0, 255, 0))

    test_img.save(folder_path + '/fill_blank/need_filled.png')

    # filling blanks
    fill_draw = ImageDraw.Draw(fill_img)
    for contour in filtered_contours:
        painted = set()
        while len(painted) < len(contour):
            for coordinate in contour:
                # filter out painted pixel
                if coordinate in painted:
                    continue

                # get surrounding color info
                surrounding_indexes = []
                surrounding_values = []
                for offset in consts.surrounding_offsets:
                    neighbour_value = fill_img.getpixel((coordinate[0] + offset[0], coordinate[1] + offset[1]))
                    surrounding_values.append(neighbour_value)
                    color_index = get_color_index(neighbour_value)
                    # add valid index
                    if color_index >= 0:
                        surrounding_indexes.append(color_index)

                # check whether there is more than two valid neighbour
                if len(surrounding_indexes) >= 2:
                    # check whether to execute complex filling or not
                    if max(surrounding_indexes) - min(surrounding_indexes) < consts.complex_fill_check_threshold:
                        average_index = sum(surrounding_indexes) * 1.0 / len(surrounding_indexes)
                        fill_draw.point(coordinate, consts.color_velocity_pairs[math.floor(average_index)][0])
                        painted.add(coordinate)
                    else:
                        echo_value = get_complex_fill_color(fill_img, coordinate, surrounding_values)
                        fill_draw.point(coordinate, echo_value)
                        painted.add(coordinate)

    return fill_img


def area_fill(folder_path, narrow_filled_img_path):
    """
    Filling blank area in radar image that which size is no more than threshold
    :param folder_path: path of result folder
    :param narrow_filled_img_path: path of narrow filled image
    :return: path of filling result image
    """
    print('  1.2: start area filling...')
    start = time.time()
    fill_img = Image.open(narrow_filled_img_path)

    # get blank pixels list
    blank_list = get_blank_list(folder_path, fill_img)

    # get blank pixels enclosure
    blank_contours = get_blank_enclosure(fill_img, blank_list)

    # fill blanks that smaller than the threshold
    filled_img = fill_blank_enclosure(folder_path, fill_img, blank_contours)

    # draw radar center area
    filled_draw = ImageDraw.Draw(filled_img)
    for x in range(consts.radar_center[0] - consts.center_diameter, consts.radar_center[0] + consts.center_diameter):
        for y in range(consts.radar_center[1] - consts.center_diameter,
                       consts.radar_center[1] + consts.center_diameter):
            distance = math.sqrt((x - consts.radar_center[0]) ** 2 + (y - consts.radar_center[1]) ** 2)
            if distance < consts.center_diameter:
                filled_draw.point((x, y), (0, 0, 0))

    end = time.time()
    duration = end - start
    print('  1.2: area filling complete!')
    print(f'  1.2: duration of area filling: {duration:.4f} seconds')

    # save area filled image
    filled_img_path = folder_path + '/fill_blank/filled.png'
    filled_img.save(filled_img_path)

    # return result image path
    return filled_img_path


def velocity_frame(filled_radar_img_path, folder_path, mode):
    start = time.time()
    print(f'  1.3: start velocity framing for mode: {mode}...')
    # set folder path of the framing result
    if mode == 'neg':
        rlt_folder_path = folder_path + '/fill_blank/neg_frames'
        scale_color = consts.negative_scale
    elif mode == 'pos':
        rlt_folder_path = folder_path + '/fill_blank/pos_frames'
        scale_color = consts.positive_scale
    else:
        print('Error mode code for velocity frame!')
        return

    # check whether the path is existed
    if not os.path.exists(rlt_folder_path):
        os.makedirs(rlt_folder_path)

    # open the radar image
    radar_img = Image.open(filled_radar_img_path)

    # iterate each color scale
    for scale_index in range(len(scale_color)):

        # create a blank velocity image
        frame_img = Image.open(consts.v_base_path)
        frame_draw = ImageDraw.Draw(frame_img)

        # iterate all pixel in the radar area
        for x in range(consts.radar_area[0], consts.radar_area[1]):
            for y in range(consts.radar_area[0], consts.radar_area[1]):
                # acquire the color of current pixel
                pixel_color = radar_img.getpixel((x, y))

                # check the color is scale color or not
                if consts.is_color_equal(pixel_color, scale_color[scale_index], 10):
                    frame_draw.point((x, y), scale_color[scale_index])

        # save the frame image
        frame_img.save(rlt_folder_path + '/' + str(scale_index) + '.png')

    end = time.time()
    duration = end - start
    print('  1.3: velocity framing complete!')
    print(f'  1.3: duration of velocity framing: {duration:.4f} seconds')


def process_rlt_saving(folder_path, read_result_path):
    print('--------------------')
    print('[1] start radar blank filling process...')
    start = time.time()
    # check result path
    if not os.path.exists(folder_path + '/fill_blank'):
        os.makedirs(folder_path + '/fill_blank')

    # execute narrow filling
    narrow_filled_img_path = narrow_fill(folder_path, read_result_path)

    # execute area filling
    filled_img_path = area_fill(folder_path, narrow_filled_img_path)

    # velocity framing
    velocity_frame(filled_img_path, folder_path, 'neg')
    velocity_frame(filled_img_path, folder_path, 'pos')

    print('[1] radar blank filling process complete!')
    end = time.time()
    duration = end - start
    print(f'[1] duration of radar blank filling process: {duration:.4f} seconds')

    return filled_img_path
