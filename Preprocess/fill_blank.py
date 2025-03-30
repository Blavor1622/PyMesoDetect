from PIL import Image, ImageDraw
import os
from tqdm import tqdm
import utils
import math
import time
import random

filled_result_folder = "fill_blank/"
filled_result_name = "gray_filled.png"
narrow_fill_debug_folder = "narrow_fill_debug/"
area_fill_debug_folder = "area_fill_debug/"


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

    # Get const values
    radar_zone = utils.get_radar_info("radar_zone")
    surrounding_offsets = utils.surrounding_offsets
    align_const = (1 + len(utils.get_color_bar_info("color_velocity_pairs"))) * 1.0 / 2
    gray_value_interval = utils.gray_value_interval

    # Iterate radar zone
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
                if max(valid_indexes) - min(valid_indexes) <= 1:
                    # Indicate that color value indexes are next to each other
                    # Use first average then round to get fill color value index
                    average_index = round((sum(valid_indexes) * 1.0) / len(valid_indexes))
                    # Calculate gray value base on the index value
                    gray_value = (average_index + 1) * gray_value_interval
                    # Compose gray RGB color
                    gray_color = (gray_value, gray_value, gray_value)
                    # Fill blank pixel
                    filled_draw.point((x, y), gray_color)
                    # Draw debug image
                    simple_fill_draw.point((x, y), gray_color)
                    only_fill_draw.point((x, y), gray_color)
                else:
                    # choose a value index that closer to velocity 0 to fill
                    # if there are more than two index have equal distance to velocity 0
                    # then use ramdom choose strategy
                    # First get aligned indexes as well as their distances to velocity 0
                    aligned_indexes = []
                    aligned_index_distances = []
                    for valid_index in valid_indexes:
                        aligned_index = valid_index + 1 - align_const
                        aligned_indexes.append(aligned_index)
                        aligned_index_distances.append(abs(aligned_index))
                    # Get the minimum distance to velocity 0
                    minimum_distance = min(aligned_index_distances)
                    # Iterate aligned indexes and record minimum distance to velocity 0 element
                    minimum_aligned_indexes = []
                    for aligned_element_idx in range(len(aligned_indexes)):
                        if aligned_index_distances[aligned_element_idx] == minimum_distance:
                            minimum_aligned_indexes.append(aligned_indexes[aligned_element_idx])
                    # randomly choose minimum aligned index
                    random_align_index = random.choice(minimum_aligned_indexes)
                    # Restore gray index value from aligned index value
                    final_value_index = round(random_align_index + align_const - 1)
                    # Calculate gray value base on the gray index value
                    gray_value = (final_value_index + 1) * gray_value_interval
                    # Compose RGB color
                    gray_color = (gray_value, gray_value, gray_value)
                    # Fill blank pixel on fill result image
                    filled_draw.point((x, y), gray_color)
                    # Draw debug image
                    complex_fill_draw.point((x, y), gray_color)
                    only_fill_draw.point((x, y), gray_color)
                # Update bar process
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
    # Get const value
    area_fill_threshold = utils.get_threshold("area_fill_threshold")
    surrounding_offsets = utils.surrounding_offsets
    narrow_fill_threshold = utils.get_threshold("narrow_fill_threshold")
    gray_value_interval = utils.gray_value_interval
    radar_zone = utils.get_radar_info("radar_zone")

    # filter blank contour
    filtered_contours = []
    for contour in blank_contours:
        if len(contour) <= area_fill_threshold:
            filtered_contours.append(contour)

    # Create debug image
    test_img = Image.new("RGB", fill_img.size, (0, 0, 0))
    test_draw = ImageDraw.Draw(test_img)
    only_area_fill_img = Image.new("RGB", fill_img.size, (255, 255, 0))
    only_area_fill_draw = ImageDraw.Draw(only_area_fill_img)
    # Draw debug image
    for contour in filtered_contours:
        for coordinate in contour:
            test_draw.point(coordinate, (0, 255, 0))
    # Save debug image
    test_img.save(folder_path + filled_result_folder + area_fill_debug_folder + 'need_area_fill.png')

    # Start area filling
    fill_draw = ImageDraw.Draw(fill_img)
    total_iterations = len(filtered_contours)
    with tqdm(total=total_iterations, desc="  Area Filling Progress", unit="enclosures") as pbar:
        for contour in filtered_contours:
            # Set for record painted pixel
            painted = set()
            while len(painted) < len(contour):
                for coordinate in contour:
                    # Filter out painted pixel
                    if coordinate in painted:
                        continue
                    # Get gray value indexes of surrounding pixels for current point
                    surrounding_indexes = []
                    valid_indexes = []
                    for offset in surrounding_offsets:
                        # Get RGB color
                        neighbour_value = fill_img.getpixel((coordinate[0] + offset[0], coordinate[1] + offset[1]))
                        # Calculate gray value index base on RGB color
                        neighbour_index = round(1.0 * neighbour_value[0] / gray_value_interval) - 1
                        surrounding_indexes.append(neighbour_index)
                        # Check whether the index is valid or not (pixel value is blank or not)
                        if neighbour_index > -1:
                            valid_indexes.append(neighbour_index)
                    # check whether there is more than two valid neighbour
                    if len(valid_indexes) >= 2:
                        # Indicate that current point can be painted
                        painted.add(coordinate)
                        # check whether to execute complex filling or not
                        if max(valid_indexes) - min(valid_indexes) <= 1:
                            # Calculate average gray value index
                            average_index = sum(valid_indexes) * 1.0 / len(valid_indexes)
                            # Calculate gray value base on average index value
                            gray_value = (round(average_index) + 1) * gray_value_interval
                            # Compose gray RGB color
                            gray_color = (gray_value, gray_value, gray_value)
                            # Fill blank pixel for fill result image
                            fill_draw.point(coordinate, gray_color)
                            # Draw debug image
                            only_area_fill_draw.point(coordinate, gray_color)
                        else:
                            # get surrounding enclosure size
                            surrounding_sizes = [0, 0, 0, 0]
                            is_found = False
                            for idx in range(len(surrounding_indexes)):
                                # Filter blank neighbour pixel
                                if surrounding_indexes[idx] < 0:
                                    continue
                                # Get neighbour coordinate that `idx` points to
                                neighbour_coordinate = (coordinate[0] + surrounding_offsets[idx][0],coordinate[1] + surrounding_offsets[idx][1])
                                # Create a set for recording visited pixels
                                visited = set()
                                # Iteration start from the neighbour pixel so add it visited first
                                visited.add(neighbour_coordinate)
                                # Create A Stack for recording need to visit pixels for the following iteration
                                stack = [neighbour_coordinate]
                                # A list for recording pixels in the same connected component with the neighbour pixel
                                component = [neighbour_coordinate]
                                # Start checking need to visit pixels
                                while stack:
                                    # threshold check for acceleration
                                    if len(component) >= narrow_fill_threshold:
                                        break
                                    current_point = stack.pop()
                                    # get surrounding pixel values
                                    for offset in surrounding_offsets:
                                        # get neighbour pixel coordinate of current point
                                        neighbour = (current_point[0] + offset[0], current_point[1] + offset[1])
                                        # radar scale check
                                        if (radar_zone[0] <= neighbour[0] <= radar_zone[1]
                                                and radar_zone[0] <= neighbour[1] <= radar_zone[1]):
                                            # Get color value of current neighbour point
                                            neighbour_value = fill_img.getpixel(neighbour)
                                            # Calculate gray value index
                                            neighbour_index = round((neighbour_value[0] / gray_value_interval)) - 1
                                            # Check whether current neighbour point is in the same velocity group
                                            if neighbour_index == surrounding_indexes[idx]:
                                                # Check current neighbour point has been visited or not
                                                # before adding to data structure
                                                if neighbour not in visited:
                                                    visited.add(neighbour)
                                                    component.append(neighbour)
                                                    stack.append(neighbour)
                                # Record connected component size to list
                                surrounding_sizes[idx] = len(component)
                                # Check component size with threshold for early ending
                                if surrounding_sizes[idx] >= narrow_fill_threshold:
                                    gray_value_index = surrounding_indexes[idx]
                                    is_found = True
                                    break
                            # Check whether there is an early ending condition matched or not
                            if not is_found:
                                # iterate the surrounding enclosure size to get maximum size neighbour
                                max_len = 0
                                max_len_idx = 0
                                for idx in range(len(surrounding_sizes)):
                                    if surrounding_sizes[idx] > max_len:
                                        max_len = surrounding_sizes[idx]
                                        max_len_idx = idx
                                gray_value_index = surrounding_indexes[max_len_idx]
                            # Calculate gray color value base on the gray index value
                            gray_value = (gray_value_index + 1) * gray_value_interval
                            # Compose gray RGB color
                            gray_color = (gray_value, gray_value, gray_value)
                            # Fill blank pixel for fill result image
                            fill_draw.point(coordinate, gray_color)
                            # Draw debug image
                            only_area_fill_draw.point(coordinate, gray_color)
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
    # area_filled_path = area_fill(folder_path, narrow_filled_path)

    end = time.time()
    duration = end - start
    print(f"[Info] Duration of radar filling: {duration:.4f} seconds")

    # Return filled image path
    return narrow_filled_path
