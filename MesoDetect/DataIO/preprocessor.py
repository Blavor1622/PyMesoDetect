"""
This file implements the logic of preprocess orignal radar image,
including turning into grayscale image and executing narrow filling.
"""
from PIL import Image, ImageDraw
import time
from tqdm import tqdm
import random
from colorama import Fore, Style
from MesoDetect.DataIO.consts import (NEED_COVER_BOUNDARY_STATIONS, BASEMAP_IMG_PATH,
                                      GRAY_SCALE_UNIT, NARROW_SURROUNDING_OFFSETS, CURRENT_DEBUG_RESULT_FOLDER)
from MesoDetect.DataIO import utils
from MesoDetect.DataIO.utils import check_output_folder
from pathlib import Path
from typing import Optional


"""
Public Interface: preprocess original radar image
"""
def radar_image_preprocess(
        img_path: Path,
        station_num: str,
        output_path: Path,
        enable_debug: bool = False
) -> Optional[Image]:
    """
    Generates a gray scale image as internal representation of input radar image
    and executes narrow for the gray scale image.
    Args:
        img_path: path of input original radar image.
        station_num: station number in string type.
        enable_debug: boolean flat that indicates whether debug mode is enabled.
        output_path: folder path for output images

    Returns:
        Gray scale image in PIL.Image format if successful.
        None otherwise.
    """
    print("[Info] Start preprocessing radar image...")
    # Generate debug folder for current module process if enable debug mode
    debug_output_path = output_path
    if enable_debug:
        debug_output_path = check_output_folder(output_path, CURRENT_DEBUG_RESULT_FOLDER)
    # Read radar data
    try:
        read_result_img = read_radar_image(img_path, station_num, debug_output_path, enable_debug)
    except Exception as e:
        print(Fore.RED + f"[Error] Exception: {e} raised when reading radar image." + Style.RESET_ALL)
        return None

    # Fill radar data
    try:
        filled_img = narrow_fill(read_result_img, debug_output_path, enable_debug)
    except Exception as e:
        print(Fore.RED + f"[Error] Exception: {e} raised when executing narrow filling." + Style.RESET_ALL)
        return None

    print("[Info] Radar image preprocessing complete.")
    return filled_img


"""
Logic implementation Function: read original radar image and convert to gray scale image
"""
def read_radar_image(radar_img_path: Path, station_num: str, image_debug_folder_path: Path, enable_debug: bool = False) -> Image:
    """
    Generates a gray image from the original radar image so that later process can basemaps on this gray image
    Args:
        radar_img_path: original radar image path
        station_num: radar station number for boundary replacement check
        image_debug_folder_path: debug output folder path
        enable_debug: flag of whether to enable debug mode or not

    Returns:
        path of gray scale image if execution success.
    """
    start = time.time()
    print("[Info] Start processing radar data...")

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
        if enable_debug:
            radar_img.save(image_debug_folder_path / "boundary_coverage.png")

    # Result images
    gray_img = Image.new("RGB", radar_img.size, (0, 0, 0))
    gray_draw = ImageDraw.Draw(gray_img)
    read_debug_img = Image.new("RGB", radar_img.size, (0, 0, 0))
    read_debug_draw = ImageDraw.Draw(read_debug_img)

    # Iterate the radar zone to read echo data
    radar_zone = utils.get_radar_info("radar_zone")
    cv_pairs = utils.get_color_bar_info("color_velocity_pairs")
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

    if enable_debug:
        gray_img.save(image_debug_folder_path / "original_gray.png")
        read_debug_img.save(image_debug_folder_path / "read_debug.png")

    end = time.time()
    duration = end - start
    print(f'[Info] Duration of radar reading: {duration:.4f} seconds')
    return gray_img


"""
Logic Implementation Function: narrow filling process 
for original gray scale image after reading from original radar image
"""
def narrow_fill(gray_img: Image, image_debug_folder_path: Path, enable_debug: bool = False) -> Image:
    """
    Executes narrow filling process for gray scale radar image, filling small gaps caused by original radar image
    region boundaries and region name marks.
    Args:
        gray_img: gray scale image
        image_debug_folder_path: debug output folder path
        enable_debug: flag of whether to enable debug mode or not

    Returns:
        filled gray scale image
    """
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
    radar_zone = utils.get_radar_info("radar_zone")
    align_const = (1 + len(utils.get_color_bar_info("color_velocity_pairs"))) * 1.0 / 2
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


    if enable_debug:
        simple_fill_img.save(image_debug_folder_path / "simple_filled.png")
        complex_fill_img.save(image_debug_folder_path / "complex_filled.png")
        only_filled_img.save(image_debug_folder_path / "only_filled.png")
        filled_img.save(image_debug_folder_path / "filled.png")
    end = time.time()
    duration = end - start
    print(f"[Info] Duration of radar filling: {duration:.4f} seconds")
    return filled_img
