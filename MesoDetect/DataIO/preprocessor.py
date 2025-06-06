from PIL import Image, ImageDraw
import os
import time
from tqdm import tqdm
import random
from colorama import Fore, Style
from MesoDetect.DataIO.consts import (NEED_COVER_BOUNDARY_STATIONS, BASEMAP_IMG_PATH,
                                      GRAY_SCALE_UNIT, NARROW_SURROUNDING_OFFSETS, CURRENT_DEBUG_RESULT_FOLDER)
from MesoDetect.DataIO import radar_config



def radar_image_preprocess(
        img_path: str,
        station_num: str,
        enable_debug: bool = False,
        image_debug_folder_path: str = ""
):
    """
    Generating a gray scale image as internal representation of input radar image.
    Args:
        img_path: path of input original radar image.
        station_num: station number in string type.
        enable_debug: boolean flat that indicates whether debug mode is enabled.
        image_debug_folder_path: images folder path.

    Returns:
        Gray scale image in PIL.Image format if successful.
        None otherwise.
    """
    print("[Info] Start preprocessing radar image...")
    # Check debug result folder if enable debug mode
    if enable_debug and image_debug_folder_path == "":
        print(Fore.RED + "[Error] There is a conflict in given argument for `get_gray_img` "
              "with image_debug_folder_path: {image_debug_folder_path} and enable_debug: {enable_debug}." + Style.RESET_ALL)
        print(Fore.RED + "[Error] Radar image preprocessing failed." + Style.RESET_ALL)
        return None

    # Read radar data
    try:
        read_result_img = read_radar_image(img_path, station_num, enable_debug, image_debug_folder_path)
    except Exception as e:
        print(Fore.RED + f"[Error] Exception: {e} raised when reading radar image." + Style.RESET_ALL)
        print(Fore.RED + "[Error] Radar image preprocessing failed." + Style.RESET_ALL)
        return None

    # Fill radar data
    try:
        filled_img = narrow_fill(read_result_img, enable_debug, image_debug_folder_path)
    except Exception as e:
        print(Fore.RED + f"[Error] Exception: {e} raised when executing narrow filling." + Style.RESET_ALL)
        print(Fore.RED + "[Error] Radar image preprocessing failed." + Style.RESET_ALL)
        return None

    print("[Info] Radar image preprocessing complete.")
    return filled_img


def read_radar_image(radar_img_path, station_num: str, enable_debug: bool = False, image_debug_folder_path: str = "") -> Image:
    """
    Generating a gray image from the original radar image
    so that later process can basemaps on this gray image
    :param radar_img_path: path of original radar image
    :param station_num: string value of the original radar station number with format "Zxxxx"
    :param enable_debug: boolean flag for deciding whether to enable debug mode
    :param image_debug_folder_path: path of debug result folder for each radar image
    :return: path of gray image if generation is success
    """
    start = time.time()
    print("[Info] Start processing radar data...")
    # Check debug result folder existence
    # Initialize empty folder path
    current_debug_folder_path = ""
    if enable_debug and image_debug_folder_path != "":
        current_debug_folder_path = image_debug_folder_path + CURRENT_DEBUG_RESULT_FOLDER
        if not os.path.exists(current_debug_folder_path):
            os.makedirs(current_debug_folder_path)

    # Open radar image
    radar_img = Image.open(radar_img_path)

    # Check whether current radar image need boundary coverage
    if station_num in NEED_COVER_BOUNDARY_STATIONS:
        coverage_draw = ImageDraw.Draw(radar_img)
        base_img = Image.open(BASEMAP_IMG_PATH + "white_boundary_" + station_num + ".png")

        # Iterate the whole zone of radar image that might covered by the white boundary
        for x in range(0, base_img.size[1]):
            for y in range(0, base_img.size[1]):
                base_pixel_value = base_img.getpixel((x, y))
                if base_pixel_value[0] > 245:
                    coverage_draw.point((x, y), (0, 0, 0))

        # Debug process
        if enable_debug and current_debug_folder_path != "":
            coverage_debug_img_path = current_debug_folder_path + "boundary_coverage.png"
            radar_img.save(coverage_debug_img_path)

    # Result images
    gray_img = Image.new("RGB", radar_img.size, (0, 0, 0))
    gray_draw = ImageDraw.Draw(gray_img)
    read_debug_img = Image.new("RGB", radar_img.size, (0, 0, 0))
    read_debug_draw = ImageDraw.Draw(read_debug_img)

    # Iterate the radar zone to read echo data
    radar_zone = radar_config.get_radar_info("radar_zone")
    cv_pairs = radar_config.get_color_bar_info("color_velocity_pairs")
    for x in range(radar_zone[0], radar_zone[1]):
        for y in range(radar_zone[0], radar_zone[1]):
            # Get current pixel value
            pixel_value = radar_img.getpixel((x, y))

            # Match echo color
            for idx in range(len(cv_pairs)):
                if all(abs(c1 - c2) <= 10 for c1, c2 in zip(pixel_value[:3], cv_pairs[idx][0][:3])):
                    gray_value = (idx + 1) * GRAY_SCALE_UNIT
                    gray_draw.point((x, y), (gray_value, gray_value, gray_value))
                    read_debug_draw.point((x, y), cv_pairs[idx][0])

    if enable_debug and current_debug_folder_path != "":
        read_result_path = current_debug_folder_path + "original_gray.png"
        gray_img.save(read_result_path)
        read_debug_img.save(current_debug_folder_path + "read_debug.png")

    end = time.time()
    duration = end - start
    print(f'[Info] duration of radar reading: {duration:.4f} seconds')
    return gray_img


def narrow_fill(gray_img: Image, enable_debug: bool = False, image_debug_folder_path: str = "") -> Image:
    start = time.time()
    print("[Info] Start filling radar image...")

    # Create result path
    filled_img = gray_img.copy()
    filled_draw = ImageDraw.Draw(filled_img)

    simple_fill_img = Image.new("RGB", filled_img.size, (0, 0, 0))
    complex_fill_img = Image.new("RGB", filled_img.size, (0, 0, 0))
    only_filled_img = Image.new("RGB", filled_img.size, (0, 0, 0))

    simple_fill_draw = ImageDraw.Draw(simple_fill_img)
    complex_fill_draw = ImageDraw.Draw(complex_fill_img)
    only_fill_draw = ImageDraw.Draw(only_filled_img)

    # Get const values
    radar_zone = radar_config.get_radar_info("radar_zone")
    align_const = (1 + len(radar_config.get_color_bar_info("color_velocity_pairs"))) * 1.0 / 2
    gray_value_interval = GRAY_SCALE_UNIT

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
                for offset in NARROW_SURROUNDING_OFFSETS:
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
                    # Calculate gray value basemap on the index value
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
                    # Calculate gray value basemap on the gray index value
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


    if enable_debug and image_debug_folder_path != "":
        current_debug_folder_path = image_debug_folder_path + CURRENT_DEBUG_RESULT_FOLDER
        if not os.path.exists(current_debug_folder_path):
            os.makedirs(current_debug_folder_path)
        simple_fill_img.save(current_debug_folder_path + "simple_filled.png")
        complex_fill_img.save(current_debug_folder_path + "complex_filled.png")
        only_filled_img.save(current_debug_folder_path + "only_filled.png")
        filled_img.save(current_debug_folder_path + "filled.png")
    end = time.time()
    duration = end - start
    print(f"[Info] Duration of radar filling: {duration:.4f} seconds")
    return filled_img
