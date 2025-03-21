from PIL import Image, ImageDraw
import os
from tqdm import tqdm
import utils
import math
import time


filled_result_folder = "fill_blank/"
filled_result_name = "gray_filled.png"
narrow_fill_debug_folder = "narrow_fill_debug/"
area_fill_debug_folder = "area_fill_debug/"


def get_neighbour_component_size(refer_image, coordinate, target_index):
    """
    get the size of the connected component that a given neighbour belong to
    :param refer_image: a PIL image object describes the adjacent relationship of given pixel
    :param coordinate: the coordinate of neighbour, which is used for getting the target color
    :param target_index: an index of gray value that represent the color index in cv_pairs
    :return: an int value that refer to the size of connected component
    """
    # get neighbour coordinate offset
    neighbour_offsets = utils.surrounding_offsets

    # Get config const data
    narrow_fill_threshold = utils.get_threshold("narrow_fill_threshold")
    radar_zone = utils.get_radar_info("radar_zone")
    gray_value_interval = utils.gray_value_interval

    # check whether is blank or not
    if target_index < 0:
        return 0

    # get connected component that neighbour belongs to
    visited = set()
    visited.add(coordinate)
    stack = [coordinate]
    component = [coordinate]

    while stack:
        # threshold check for acceleration
        if len(component) >= narrow_fill_threshold:
            break
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
                neighbour_index = round((neighbour_value[0] / gray_value_interval)) - 1
                if neighbour_index == target_index:
                    neighbours.append(neighbour)

        for neighbour in neighbours:
            if neighbour not in visited:
                visited.add(neighbour)
                component.append(neighbour)
                stack.append(neighbour)

    return len(component)


def get_complex_fill_index(radar_img, current_coordinate, surrounding_indexes):
    """
    A dependency function for getting the color that for current coordinate by using complex filling
    :param radar_img: a PIL image object that is used for getting the connected component size of neighbour echo
    :param current_coordinate: the coordinate of current blank pixel that need complex filling
    :param surrounding_indexes: list of surrounding neighbour pixel value indexes after transformation
    :return: an index of gray value for filling
    """
    # Get const config data
    surrounding_offsets = utils.surrounding_offsets
    narrow_fill_threshold = utils.get_threshold("narrow_fill_threshold")

    # get surrounding enclosure size
    surrounding_sizes = [0, 0, 0, 0]
    for idx in range(len(surrounding_indexes)):
        # filter out blank neighbour pixel
        if surrounding_indexes[idx] < 0:
            continue

        # get size enclosure for surrounding echo
        surrounding_sizes[idx] = get_neighbour_component_size(radar_img,
                                                             (current_coordinate[0] + surrounding_offsets[idx][0],
                                                              current_coordinate[1] + surrounding_offsets[idx][1]), surrounding_indexes[idx])
        # process accelerate
        if surrounding_sizes[idx] >= narrow_fill_threshold:
            return surrounding_indexes[idx]

    # iterate the surrounding enclosure size to get maximum size neighbour
    max_len = 0
    max_len_idx = 0
    for idx in range(len(surrounding_sizes)):
        if surrounding_sizes[idx] > max_len:
            max_len = surrounding_sizes[idx]
            max_len_idx = idx

    return surrounding_indexes[max_len_idx]


def narrow_fill(folder_path, gray_img_path):
    print("  [1] Start narrow filling...")
    # Open gray radar image
    gray_img = Image.open(gray_img_path)

    # Create result path
    filled_img = Image.open(gray_img_path)
    filled_draw = ImageDraw.Draw(filled_img)

    # Debug image
    # Check debug result folder
    if not os.path.exists(folder_path + filled_result_folder + narrow_fill_debug_folder):
        os.makedirs(folder_path + filled_result_folder + narrow_fill_debug_folder)
    simple_fill_img = Image.new("RGB", filled_img.size, (0, 0, 0))
    complex_fill_img = Image.new("RGB", filled_img.size, (0, 0, 0))
    only_filled_img = Image.new("RGB", filled_img.size, (0, 0, 0))

    simple_fill_draw = ImageDraw.Draw(simple_fill_img)
    complex_fill_draw = ImageDraw.Draw(complex_fill_img)
    only_fill_draw = ImageDraw.Draw(only_filled_img)

    # Iterate radar zone
    radar_zone = utils.get_radar_info("radar_zone")
    surrounding_offsets = utils.surrounding_offsets
    complex_fill_threshold = utils.get_threshold("complex_fill_threshold")
    gray_value_interval = utils.gray_value_interval

    total_iterations = (radar_zone[1] - radar_zone[0]) ** 2
    with tqdm(total=total_iterations, desc="  Narrow Filling Progress", unit="pixels") as pbar:
        for x in range(radar_zone[0], radar_zone[1]):
            for y in range(radar_zone[0], radar_zone[1]):
                # Get current pixel value
                pixel_value = gray_img.getpixel((x, y))

                # Calculate cv index according to the gray value
                index = round(pixel_value[0] * 1.0 / gray_value_interval) - 1

                # Filter out no blank pixel
                if not index == -1:
                    pbar.update(1)
                    continue

                # Get surrounding pixel color value info
                surrounding_indexes = []
                for offset in surrounding_offsets:
                    neighbour_value = gray_img.getpixel((x + offset[0], y + offset[1]))
                    surrounding_index = round(neighbour_value[0] * 1.0 / gray_value_interval) - 1
                    surrounding_indexes.append(surrounding_index)

                # Check whether the current pixel neighbours satisfy narrow fill condition
                if (not (surrounding_indexes[0] > -1 and surrounding_indexes[1] > -1
                         or surrounding_indexes[2] > -1 and surrounding_indexes[3] > -1)):
                    pbar.update(1)
                    continue

                # Execute Direct filling if only one side with same echo color
                if (surrounding_indexes[0] == surrounding_indexes[1] and surrounding_indexes[0] > -1
                        and surrounding_indexes[2] == surrounding_indexes[3] and surrounding_indexes[2] < 0):
                    gray_value = (surrounding_indexes[0] + 1) * gray_value_interval
                    filled_draw.point((x, y), (gray_value, gray_value, gray_value))
                    simple_fill_draw.point((x, y), (gray_value, gray_value, gray_value))
                    only_fill_draw.point((x, y), (gray_value, gray_value, gray_value))
                    pbar.update(1)
                    continue

                if (surrounding_indexes[2] == surrounding_indexes[3] and surrounding_indexes[2] > -1
                        and surrounding_indexes[0] == surrounding_indexes[1] and surrounding_indexes[0] < 0):
                    gray_value = (surrounding_indexes[2] + 1) * gray_value_interval
                    filled_draw.point((x, y), (gray_value, gray_value, gray_value))
                    simple_fill_draw.point((x, y), (gray_value, gray_value, gray_value))
                    only_fill_draw.point((x, y), (gray_value, gray_value, gray_value))
                    pbar.update(1)
                    continue

                # Get valid indexes
                valid_indexes = []
                for index in surrounding_indexes:
                    if index > -1:
                        valid_indexes.append(index)

                # Check whether to execute complex fill or not
                if max(valid_indexes) - min(valid_indexes) < complex_fill_threshold:
                    average_index = round((sum(valid_indexes) * 1.0) / len(valid_indexes))
                    gray_value = (average_index + 1) * gray_value_interval
                    filled_draw.point((x, y), (gray_value, gray_value, gray_value))
                    simple_fill_draw.point((x, y), (gray_value, gray_value, gray_value))
                    only_fill_draw.point((x, y), (gray_value, gray_value, gray_value))
                    pbar.update(1)
                else:
                    # Get complex fill gray color index
                    complex_fill_index = get_complex_fill_index(gray_img, (x, y), surrounding_indexes)
                    gray_value = (complex_fill_index + 1) * gray_value_interval
                    filled_draw.point((x, y), (gray_value, gray_value, gray_value))
                    complex_fill_draw.point((x, y), (gray_value, gray_value, gray_value))
                    only_fill_draw.point((x, y), (gray_value, gray_value, gray_value))
                    pbar.update(1)

    # Save filled image
    filled_img_path = folder_path + filled_result_folder + filled_result_name
    filled_img.save(filled_img_path)

    # Save debug image
    simple_fill_img.save(folder_path + filled_result_folder + narrow_fill_debug_folder + "simple_fill.png")
    complex_fill_img.save(folder_path + filled_result_folder + narrow_fill_debug_folder + "complex_fill.png")
    only_filled_img.save(folder_path + filled_result_folder + narrow_fill_debug_folder + "only_fill.png")

    print("  [1] Narrow filling finished.")
    return filled_img_path


def get_blank_list(fill_img):
    """
    this function iterate the original filled image and return a list of blank pixels in it
    :param fill_img: the Image object of original filled image
    :return: list of blank pixels of original filled image
    """
    # Get const config data
    radar_zone = utils.get_radar_info("radar_zone")
    radar_center = utils.get_radar_info("radar_center")
    zone_diameter = utils.get_radar_info("zone_diameter")
    gray_value_interval = utils.gray_value_interval

    # iterate the radar image to get a list of blank pixel
    blank_list = []
    for x in range(radar_zone[0], radar_zone[1]):
        for y in range(radar_zone[0], radar_zone[1]):
            if math.sqrt(
                    (x - radar_center[0]) ** 2 + (y - radar_center[1]) ** 2) >= zone_diameter - 1:
                continue
            # get current pixel value
            pixel_value = fill_img.getpixel((x, y))
            gray_value_index = round(pixel_value[0] * 1.0 / gray_value_interval) - 1

            if gray_value_index < 0:
                blank_list.append((x, y))

    return blank_list


def get_blank_enclosure(fill_img, blank_list):
    """
    this function iterates the list of blank pixels list and groups them into enclosures
    in which pixels are next to each other
    :param fill_img: the original filled image
    :param blank_list: list of blank pixels
    :return: list of enclosure of blank pixels
    """
    # Get const config data
    radar_zone = utils.get_radar_info("radar_zone")
    neighbour_offsets = utils.surrounding_offsets
    gray_value_interval = utils.gray_value_interval

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

                # Add neighbour coordinate if it is a blank pixel
                adjacent_pixels = []
                for offset in neighbour_offsets:
                    # Get pixel value
                    neighbour_coordinate = (current_pixel[0] + offset[0], current_pixel[1] + offset[1])
                    neighbour_value = fill_img.getpixel(neighbour_coordinate)
                    neighbour_gray_index = round(neighbour_value[0] * 1.0 / gray_value_interval) - 1
                    if neighbour_gray_index < 0:
                        adjacent_pixels.append(neighbour_coordinate)

                # iterate all neighbours
                for neighbour in adjacent_pixels:
                    # note that the neighbour pixel might out of radar range
                    if (not radar_zone[0] <= neighbour[0] <= radar_zone[1]
                            or not radar_zone[0] <= neighbour[1] <= radar_zone[1]):
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
    # Get const config data
    area_fill_threshold = utils.get_threshold("area_fill_threshold")
    complex_fill_threshold = utils.get_threshold("complex_fill_threshold")
    surrounding_offsets = utils.surrounding_offsets
    gray_value_interval = utils.gray_value_interval

    # filter blank contour
    filtered_contours = []
    for contour in blank_contours:
        if len(contour) <= area_fill_threshold:
            filtered_contours.append(contour)

    test_img = Image.new("RGB", fill_img.size, (0, 0, 0))
    test_draw = ImageDraw.Draw(test_img)

    for contour in filtered_contours:
        for coordinate in contour:
            test_draw.point(coordinate, (0, 255, 0))

    test_img.save(folder_path + filled_result_folder + area_fill_debug_folder + 'need_area_fill.png')

    # filling blanks
    fill_draw = ImageDraw.Draw(fill_img)
    only_area_fill_img = Image.new("RGB", fill_img.size, (255, 255, 0))
    only_area_fill_draw = ImageDraw.Draw(only_area_fill_img)

    total_iterations = len(filtered_contours)
    with tqdm(total=total_iterations, desc="  Area Filling Progress", unit="enclosures") as pbar:
        for contour in filtered_contours:
            painted = set()
            while len(painted) < len(contour):
                for coordinate in contour:
                    # filter out painted pixel
                    if coordinate in painted:
                        continue

                    # get surrounding color info
                    surrounding_indexes = []
                    valid_indexes = []
                    for offset in surrounding_offsets:
                        neighbour_value = fill_img.getpixel((coordinate[0] + offset[0], coordinate[1] + offset[1]))
                        neighbour_index = round(1.0 * neighbour_value[0] / gray_value_interval) - 1
                        surrounding_indexes.append(neighbour_index)

                        # Check whether the index is valid or not (pixel value is blank or not)
                        if neighbour_index > -1:
                            valid_indexes.append(neighbour_index)

                    # check whether there is more than two valid neighbour
                    if len(valid_indexes) >= 2:
                        # check whether to execute complex filling or not
                        if max(valid_indexes) - min(valid_indexes) < complex_fill_threshold:
                            average_index = sum(valid_indexes) * 1.0 / len(valid_indexes)
                            gray_value = (round(average_index) + 1) * gray_value_interval
                            fill_draw.point(coordinate, (gray_value, gray_value, gray_value))
                            only_area_fill_draw.point(coordinate, (gray_value, gray_value, gray_value))
                            painted.add(coordinate)
                        else:
                            gray_value_index = get_complex_fill_index(fill_img, coordinate, surrounding_indexes)
                            gray_value = (gray_value_index + 1) * gray_value_interval
                            fill_draw.point(coordinate, (gray_value, gray_value, gray_value))
                            only_area_fill_draw.point(coordinate, (gray_value, gray_value, gray_value))
                            painted.add(coordinate)
            pbar.update(1)
    # Save debug image
    only_area_fill_img.save(folder_path + filled_result_folder + area_fill_debug_folder + 'only_area_fill.png')

    return fill_img


def area_fill(folder_path, narrow_filled_img_path):
    """
    Filling blank area in radar image that which size is no more than threshold
    :param folder_path: path of result folder
    :param narrow_filled_img_path: path of narrow filled image
    :return: path of filling result image
    """
    print('  [2] Start area filling...')

    fill_img = Image.open(narrow_filled_img_path)

    # Check debug result folder
    if not os.path.exists(folder_path + filled_result_folder + area_fill_debug_folder):
        os.makedirs(folder_path + filled_result_folder + area_fill_debug_folder)

    # get blank pixels list
    blank_list = get_blank_list(fill_img)

    # Debug blank pixel list content
    blanks_img = Image.new("RGB", fill_img.size, (0, 0, 0))
    blanks_draw = ImageDraw.Draw(blanks_img)

    for coordinate in blank_list:
        blanks_draw.point(coordinate, (0, 255, 0))

    blanks_img.save(folder_path + filled_result_folder + area_fill_debug_folder + "blanks.png")

    # get blank pixels enclosure
    blank_contours = get_blank_enclosure(fill_img, blank_list)

    # Debug blank pixel list content
    blank_enclosure_img = Image.new("RGB", fill_img.size, (0, 0, 0))
    blank_enclosure_draw = ImageDraw.Draw(blank_enclosure_img)

    for enclosure in blank_contours:
        for coordinate in enclosure:
            blank_enclosure_draw.point(coordinate, (0, 255, 0))

    blank_enclosure_img.save(folder_path + filled_result_folder + area_fill_debug_folder + "blank_enclosures.png")

    # fill blanks that smaller than the threshold
    filled_img = fill_blank_enclosure(folder_path, fill_img, blank_contours)

    # save area filled image
    filled_img_path = folder_path + filled_result_folder + filled_result_name
    filled_img.save(filled_img_path)

    print("  [2] Area filling finished.")
    # return result image path
    return filled_img_path


def fill_radar_image(folder_path, gray_img_path):
    """
    Filling blanks in the radar image that covered by boundaries, range ring and place name mark,
    Generating a filled image that keep the consistency of same value echoed groups as possible
    for latter analysis
    :param gray_img_path: path of gray image that generated by read_data.py module
    :param folder_path: path of result folder
    :return: path of filled image
    """
    start = time.time()
    print("[Info] Start filling radar image...")
    # Check result path
    if not os.path.exists(folder_path + filled_result_folder):
        os.makedirs(folder_path + filled_result_folder)

    # Execute narrow filling
    narrow_filled_path = narrow_fill(folder_path, gray_img_path)

    # Execute area filling
    area_filled_path = area_fill(folder_path, narrow_filled_path)

    end = time.time()
    duration = end - start
    print(f"[Info] Duration of radar filling: {duration:.4f} seconds")

    # Return filled image path
    return area_filled_path
