from PIL import Image, ImageDraw
import os
from tqdm import tqdm
import utils
import time
import random

filled_result_folder = "fill_blank/"
filled_result_name = "gray_filled.png"
narrow_fill_debug_folder = "narrow_fill_debug/"


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

    end = time.time()
    duration = end - start
    print(f"[Info] Duration of radar filling: {duration:.4f} seconds")

    # Return filled image path
    return narrow_filled_path

