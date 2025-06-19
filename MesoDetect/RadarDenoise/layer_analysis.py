from PIL import Image, ImageDraw
from MesoDetect.RadarDenoise import dependencies, consts
from MesoDetect.DataIO.consts import GRAY_SCALE_UNIT, SURROUNDING_OFFSETS
from MesoDetect.DataIO.radar_config import get_color_bar_info, get_radar_info
from typing import List, Tuple
from pathlib import Path

"""
    Interface: get_denoise_img
"""
# regard debug_output_path is valid when calling this interface
def get_denoise_img(
        fill_img: Image,
        layer_model: List[List[Tuple[int, int]]],
        mode: str, enable_debug: bool,
        debug_output_path: Path
) -> Image:
    """
    denoise given filled image and return denoised result image
    Args:
        fill_img: PIL Image Object of narrow filled image
        layer_model: list of layer echoes
        mode: string that indicates the velocity mode
        enable_debug: boolean flag, True for enabling debug mode and False for disabling
        debug_output_path: pathlib path type of output image path

    Returns:
    PIL Image object of a denoised image
    """
    print(f"[Info] Start generating {mode} denoise image...")
    # Get basemaps echo image: Filter out Image Scale isolated echo group and draw echoes with two valid channel color
    denoise_img = get_base_echo_img(layer_model, fill_img.size, mode)
    if enable_debug:
        denoise_img.save(debug_output_path / (mode + "_base.png"))

    # Layer filter process: Draw large echo groups in Layer Scale and inner fill them for the holes in them and get small echo groups
    denoise_img, small_echo_groups = layer_filter(fill_img, mode, denoise_img, layer_model, enable_debug, debug_output_path)

    # Small echo groups analysis: Draw echoes that does not exceed below or surrounding layer gap
    denoise_img = small_echo_group_analysis(fill_img, denoise_img, mode, small_echo_groups, enable_debug, debug_output_path)

    # Remove small isolated echo that is basemaps on the basemaps echo
    denoise_img = remove_small_isolated_groups(denoise_img, len(layer_model), mode, enable_debug, debug_output_path)

    # Filling basemaps echo area
    denoise_img = base_echo_fill(denoise_img, len(layer_model), mode)

    # Remove basemaps echoes
    denoise_img = remove_base_echoes(denoise_img, len(layer_model), mode, enable_debug, debug_output_path)

    # Save debug image
    if enable_debug:
        denoise_img.save(debug_output_path / (mode + "_denoised.png"))

    print(f"[Info] {mode} denoise image generation success.")
    return denoise_img


"""
    Internal dependency functions
"""
def remove_base_echoes(denoise_img: Image, layer_model_len: int, mode: str, enable_debug: bool, debug_result_folder: Path) -> Image:
    # Check mode code
    base_value_index, _ = check_velocity_mode(mode, layer_model_len)

    # Debug image for process
    remove_debug_img = Image.new("RGB", denoise_img.size, (0, 0, 0))
    remove_debug_draw = ImageDraw.Draw(remove_debug_img)

    denoise_draw = ImageDraw.Draw(denoise_img)
    # Iterate radar zone to filter out basemaps echoes, but keep basemaps filled echoes
    radar_zone = get_radar_info("radar_zone")
    for x in range(radar_zone[0], radar_zone[1]):
        for y in range(radar_zone[0], radar_zone[1]):
            # Extract the second and third channel RGB color value for distinguish basemaps echo pixel
            pixel_value = denoise_img.getpixel((x, y))
            second_channel = pixel_value[1]
            third_channel = pixel_value[2]
            second_channel_index = round(second_channel / GRAY_SCALE_UNIT) - 1
            third_channel_index = round(third_channel / GRAY_SCALE_UNIT) - 1
            # Only basemaps echo that have different value in second and third channel RGB color
            if second_channel_index != third_channel_index:
                # Indicate that current pixel is basemaps echo
                denoise_draw.point((x, y), (0, 0, 0))
                remove_debug_draw.point((x, y), (0, 255, 0))

    # Save debug image
    if enable_debug:
        remove_debug_img.save(debug_result_folder / (mode + "_base_remove.png"))

    return denoise_img


def remove_small_isolated_groups(denoise_img: Image, layer_model_len: int, mode: str, enable_debug: bool, debug_result_folder: Path) -> Image:
    """
    Remove small isolated groups that is only surrounded by basemaps echoes in Image Scale,
    and inner fill the image after that.
    Args:
        denoise_img: PIL Image object of denoised image
        layer_model_len: length of layer model in Int value type
        mode: velocity mode code in str type, only allowed to be "neg" or "pos"
        enable_debug:
        debug_result_folder: str type of debug result folder path

    Returns:
        PIL Image object of denoised image that has removed isolated echo groups
    """
    # Check mode code
    base_index, _ = check_velocity_mode(mode, layer_model_len)

    # Get refer image for basemaps echo exclusion
    exclude_base_img = Image.new("RGB", denoise_img.size, (0, 0, 0))
    exclude_base_draw = ImageDraw.Draw(exclude_base_img)
    radar_zone = get_radar_info("radar_zone")
    # Iterate radar zone and get target echo list as well as drawing refer image
    exclude_img_echo_list = []
    for x in range(radar_zone[0], radar_zone[1]):
        for y in range(radar_zone[0], radar_zone[1]):
            # Get pixel value from denoise image
            pixel_value = denoise_img.getpixel((x, y))
            # Calculate value index, use the second channel value for excluding basemaps echo
            pixel_index = round(pixel_value[1] / GRAY_SCALE_UNIT) - 1
            if pixel_index >= 0:
                exclude_img_echo_list.append((x, y))
                exclude_base_draw.point((x, y), consts.REFER_IMG_COLOR)
    if enable_debug:
        exclude_base_img.save(debug_result_folder / (mode + "_exclude_base.png"))

    # Get echo groups from exclude basemaps image
    exclude_base_echo_groups = dependencies.get_echo_groups(exclude_base_img, exclude_img_echo_list)

    # Check group size for each group
    remove_debug_img = Image.new("RGB", denoise_img.size, (0, 0, 0))
    remove_debug_draw = ImageDraw.Draw(remove_debug_img)
    denoise_draw = ImageDraw.Draw(denoise_img)
    for echo_group in exclude_base_echo_groups:
        if len(echo_group) < consts.SMALL_GROUP_SIZE_THRESHOLD:
            # Remove small isolated groups that smaller than threshold from denoise image
            for echo_coord in echo_group:
                denoise_draw.point(echo_coord, (0, 0, 0))
                remove_debug_draw.point(echo_coord, (0, 255, 0))
    # Execute inner filling for denoise after exclude basemaps echo isolated echo groups removing
    base_color_value = (base_index + 1) * GRAY_SCALE_UNIT
    denoise_img = dependencies.inner_filling(denoise_img, (base_color_value, 0, base_color_value), denoise_img)

    # Save debug img
    if enable_debug:
        remove_debug_img.save(debug_result_folder / (mode + "_exclude_remove.png"))
    return denoise_img


def small_echo_group_analysis(
        fill_img: Image,
        denoise_img: Image, mode: str,
        small_echo_groups: List[List[Tuple[int, int]]],
        enable_debug: bool,
        debug_result_folder: Path
) -> Image:
    # Check mode code
    is_reverse = check_velocity_mode(mode)

    denoise_draw = ImageDraw.Draw(denoise_img)
    for small_group in small_echo_groups:
        # Get below echo value of current group
        # There are three cases:
        #   1. valid echo with full RGB color from large group inner filling(velocity >= 0)
        #   2. basemaps echo with two channel RGB color from basemaps echo(velocity 0)
        #   3. empty basemaps
        below_value = denoise_img.getpixel(small_group[0])
        # Calculate below value index using the second channel value
        below_value_index = round(1.0 * below_value[1] / GRAY_SCALE_UNIT) - 1

        # Calculate small group actual value index
        current_group_value = fill_img.getpixel(small_group[0])
        current_group_index = round(1.0 * current_group_value[0] / GRAY_SCALE_UNIT) - 1
        # Note that the absolute value of velocity is required to be increasing in this process when below echo is valid
        if below_value_index >= 0:
            # Indicate that current group is above valid echoes
            # Only draw current group when it does not exceed layer index gap
            if not is_reverse and 0 <= current_group_index - below_value_index <= consts.LAYER_GAP_THRESHOLD:
                # Indicate that current mode is pos
                for echo_coordinate in small_group:
                    denoise_draw.point(echo_coordinate, current_group_value)
            elif is_reverse and 0 <= below_value_index - current_group_index <= consts.LAYER_GAP_THRESHOLD:
                # Indicate that current mode is neg
                for echo_coordinate in small_group:
                    denoise_draw.point(echo_coordinate, current_group_value)
        else:
            # Indicate that current group is above basemaps echoes or just empty
            base_below_index = round(1.0 * below_value[0] / GRAY_SCALE_UNIT) - 1
            if base_below_index >= 0:
                # Indicate that no empty but is basemaps echo
                # Get surroundings
                surroundings = set()
                valid_surroundings = set()
                valid_surrounding_indexes = []
                for echo_coordinate in small_group:
                    # Get valid echo neighbour coordinates
                    for offset in SURROUNDING_OFFSETS:
                        neighbour_coordinate = (echo_coordinate[0] + offset[0], echo_coordinate[1] + offset[1])
                        # Use filled image to calculate the surrounding set instead of denoise image
                        neighbour_value = denoise_img.getpixel(neighbour_coordinate)[1]
                        neighbour_index = round(neighbour_value / GRAY_SCALE_UNIT) - 1
                        if neighbour_coordinate not in small_group:
                            if neighbour_coordinate not in surroundings:
                                surroundings.add(neighbour_coordinate)
                        if neighbour_index >= 0:
                            # Indicate that current neighbour is a valid surrounding
                            if neighbour_coordinate not in valid_surroundings:
                                valid_surroundings.add(neighbour_coordinate)
                                valid_surrounding_indexes.append(neighbour_index)
                if len(valid_surrounding_indexes) > 0:
                    # indicate that there are valid surrounding for current small group
                    # Check valid echo surrounded ratio, if satisfies condition then check layer gap
                    valid_surrounded_ratio = len(valid_surroundings) / len(surroundings)
                    if valid_surrounded_ratio >= consts.VALID_SURROUNDED_ECHO_RATIO_THRESHOLD:
                        # Calculate average value index
                        avg_surrounding_index = sum(valid_surrounding_indexes) / len(valid_surrounding_indexes)
                        # Check with threshold
                        if abs(current_group_index - avg_surrounding_index) <= consts.LAYER_GAP_THRESHOLD:
                            for echo_coordinate in small_group:
                                denoise_draw.point(echo_coordinate, current_group_value)
                        else:
                            # Indicate that current small group exceed the gap threshold with valid surroundings
                            # Calculate approximate average value index
                            round_avg_index = round(avg_surrounding_index)
                            round_avg_value = (round_avg_index + 1) * GRAY_SCALE_UNIT
                            for echo_coordinate in small_group:
                                denoise_draw.point(echo_coordinate, (round_avg_value, round_avg_value, round_avg_value))
                else:
                    # Indicate that current small group has not valid surroundings
                    # Check with basemaps below index
                    if abs(current_group_index - base_below_index) <= consts.LAYER_GAP_THRESHOLD:
                        for echo_coordinate in small_group:
                            denoise_draw.point(echo_coordinate, current_group_value)
            # Groups that above empty is not drawn and is filtered out
            # Because in the process of getting basemaps echo image, Image Scale small groups is removed

    # Save debug img
    if enable_debug:
        denoise_img.save(debug_result_folder / (mode + "_small_filter.png"))
    return denoise_img


def layer_filter(fill_img: Image, mode: str, denoise_img: Image, layer_model: List[List[Tuple[int, int]]], enable_debug: bool, debug_result_folder: Path):
    """
    Execute layer filter process, for each layer, draw large trustworthy echo group and then inner filling the whole in them,
    in the meantime, collect small echo groups in Layer Scale for latter analysis
    """
    # Check mode code
    base_index, layer_range = check_velocity_mode(mode, len(layer_model))

    # Keep echo groups which size exceed size threshold that is more likely to be trustful
    denoise_draw = ImageDraw.Draw(denoise_img)
    small_echo_groups = []
    cv_pairs = get_color_bar_info("color_velocity_pairs")
    for layer_idx in layer_range:
        # Create a debug image for each layer
        layer_debug_img = Image.new("RGB", denoise_img.size, (0, 0, 0))
        layer_debug_draw = ImageDraw.Draw(layer_debug_img)

        # Calculate gray color value for current layer
        layer_echo_value = (layer_idx + 1) * GRAY_SCALE_UNIT
        echo_color = (layer_echo_value, layer_echo_value, layer_echo_value)

        # Create an inner filling refer image
        inner_fill_refer_img = Image.new("RGB", denoise_img.size, (0, 0, 0))
        inner_fill_refer_draw = ImageDraw.Draw(inner_fill_refer_img)

        # Get echo groups for current layer
        echo_groups = dependencies.get_echo_groups(fill_img, layer_model[layer_idx])

        # Draw echo groups that bigger than size threshold
        for echo_group in echo_groups:
            # Huge echo skip denoise
            if len(echo_group) >= consts.SMALL_GROUP_SIZE_THRESHOLD:
                for echo_coordinate in echo_group:
                    denoise_draw.point(echo_coordinate, echo_color)
                    inner_fill_refer_draw.point(echo_coordinate, echo_color)
                    layer_debug_draw.point(echo_coordinate, cv_pairs[layer_idx][0])
            # In the meantime get small echo groups list
            else:
                if len(echo_group) > 0:
                    small_echo_groups.append(echo_group)
        # Execute inner filling for each layer with valid full RGB color
        denoise_img = dependencies.inner_filling(inner_fill_refer_img, echo_color, denoise_img)
        layer_debug_img = dependencies.inner_filling(inner_fill_refer_img, (255, 0, 255), layer_debug_img)
        denoise_draw = ImageDraw.Draw(denoise_img)
        if enable_debug:
            layer_debug_img.save(debug_result_folder / (mode + "_layer_debug_" + str(layer_idx) + ".png"))
    # Save debug image
    if enable_debug:
        denoise_img.save(debug_result_folder / (mode + "_smooth.png"))
    return denoise_img, small_echo_groups


"""
Note: image scale small group and layer scale small group are distinct. 
"""
def get_base_echo_img(layer_model: List[List[Tuple[int, int]]], radar_img_size: Tuple[int, int], mode: str) -> Image:
    """
    Generate an inner filled basemaps echo image with two valid channel color
    that has remove image scale small echo groups. This image is useful for latter analysis
    including denoise and velocity unfold
    Args:
        layer_model: list of layer echoes
        radar_img_size: size of radar image
        mode: a string that indicate the velocity mode

    Returns:
        A PIL Image Object of basemaps velocity image
    """
    # Check mode code
    base_index, layer_range = check_velocity_mode(mode, len(layer_model))

    # Create an empty image
    base_img = Image.new("RGB", radar_img_size, (0, 0, 0))
    base_draw = ImageDraw.Draw(base_img)
    # Get basic values
    base_value = GRAY_SCALE_UNIT * (base_index + 1)
    # Use two valid channel color to distinguish basemaps echo
    base_color = (base_value, 0, base_value)
    # Iterate each layer for draw all echo as basemaps echo
    for layer_idx in layer_range:
        for echo_coordinate in layer_model[layer_idx]:
            base_draw.point(echo_coordinate, base_color)

    # Execute inner filling which might be useful for velocity unfold
    base_img = dependencies.inner_filling(base_img, base_color, base_img)

    # Get all basemaps echo pixel coordinate
    echo_pixel_list = []
    radar_zone = get_radar_info("radar_zone")
    for x in range(radar_zone[0], radar_zone[1]):
        for y in range(radar_zone[0], radar_zone[1]):
            # Get current pixel value
            pixel_coordinate = (x, y)
            pixel_value = base_img.getpixel(pixel_coordinate)[0]
            # Calculate color value index of the pixel
            pixel_index = round(1.0 * pixel_value / GRAY_SCALE_UNIT) - 1
            if pixel_index != -1:
                echo_pixel_list.append(pixel_coordinate)

    # Get basemaps echo groups
    echo_groups = dependencies.get_echo_groups(base_img, echo_pixel_list)

    # Get list of basemaps echo groups that smaller than the size threshold
    removed_groups = []
    for echo_group in echo_groups:
        if len(echo_group) < consts.SMALL_GROUP_SIZE_THRESHOLD:
            removed_groups.append(echo_group)

    # Cover the small groups with empty value for removing
    base_draw = ImageDraw.Draw(base_img)
    for echo_group in removed_groups:
        for echo_coordinate in echo_group:
            base_draw.point(echo_coordinate, (0, 0, 0))

    # Return result image
    return base_img


def base_echo_fill(gray_img: Image, layer_model_len: int, mode: str) -> Image:
    """
    Analise all basemaps echo groups and fill them basemaps on the valid surrounding echo values
    when surrounded ratio exceed threshold. The filling color is one valid channel RGB color.
    Args:
        gray_img: gray value image in PIL Image object type that has basemaps echoes
        layer_model_len: len of echo layer list
        mode: string value that indicate the velocity mode

    Returns: a filled image in PIL Image object type

    """
    # Check mode code
    base_index, _ = check_velocity_mode(mode, layer_model_len)

    # get basemaps echo color value
    base_color_value = (base_index + 1) * GRAY_SCALE_UNIT
    base_color = (base_color_value, base_color_value, base_color_value)

    # Create a refer image for grouping
    refer_img = Image.new("RGB", gray_img.size, (0, 0, 0))
    refer_draw = ImageDraw.Draw(refer_img)

    # Iterate radar zone to get need fill area
    radar_zone = get_radar_info("radar_zone")
    base_echo_list = []
    for x in range(radar_zone[0], radar_zone[1]):
        for y in range(radar_zone[0], radar_zone[1]):
            # Get current pixel value
            pixel_value = gray_img.getpixel((x, y))
            # Calculate gray value index
            pixel_index_0 = round(pixel_value[0] / GRAY_SCALE_UNIT) - 1     # First channel value
            pixel_index_1 = round(pixel_value[1] / GRAY_SCALE_UNIT) - 1     # Second channel value
            # Check whether is basemaps echo or not
            if pixel_index_0 != pixel_index_1:
                base_echo_list.append((x, y))
                refer_draw.point((x, y), base_color)

    # Get basemaps echo groups
    base_echo_groups = dependencies.get_echo_groups(refer_img, base_echo_list)
    # Analise each group's surrounding
    gray_draw = ImageDraw.Draw(gray_img)
    for echo_group in base_echo_groups:
        # First get surrounded valid indexes
        surroundings = set()
        valid_surrounding_indexes = []
        for echo_coordinate in echo_group:
            for offset in SURROUNDING_OFFSETS:
                neighbour_coordinate = (echo_coordinate[0] + offset[0], echo_coordinate[1] + offset[1])
                neighbour_value = gray_img.getpixel(neighbour_coordinate)
                neighbour_index_0 = round(neighbour_value[0] / GRAY_SCALE_UNIT) - 1
                neighbour_index_1 = round(neighbour_value[1] / GRAY_SCALE_UNIT) - 1
                if neighbour_index_0 == neighbour_index_1:
                    # Indicate that current neighbor is not basemaps echo
                    if neighbour_coordinate not in surroundings:
                        # Note that surroundings set might include empty pixel coord
                        surroundings.add(neighbour_coordinate)
                        if neighbour_index_0 >= 0:
                            # Add valid echo indexes into list
                            valid_surrounding_indexes.append(neighbour_index_0)
        if len(surroundings) == 0:
            continue
        surrounded_ratio = len(valid_surrounding_indexes) / len(surroundings)
        # Fill basemaps echo group with average surrounded valid echo value when exceed surrounded ratio
        if surrounded_ratio >= consts.BASE_ECHO_SURROUNDED_RATIO_THRESHOLD:
            # Calculate average surrounding index
            avg_surrounding_idx = sum(valid_surrounding_indexes) / len(valid_surrounding_indexes)
            round_avg_idx = round(avg_surrounding_idx)
            avg_value = (round_avg_idx + 1) * GRAY_SCALE_UNIT
            for echo_coordinate in echo_group:
                # Note that the basemaps filling value is one valid channel RGB color
                gray_draw.point(echo_coordinate, (avg_value, 0, 0))
    return gray_img


def check_velocity_mode(mode: str, layer_model_len: int = -1):
    if mode == "neg":
        if layer_model_len != -1:
            base_index = round(layer_model_len / 2) - 1
            layer_range = range(base_index, -1, -1)
            return base_index, layer_range
        else:
            is_reverse = True
            return is_reverse
    elif mode == "pos":
        if layer_model_len != -1:
            base_index = round(layer_model_len / 2)
            layer_range = range(base_index, layer_model_len)
            return base_index, layer_range
        else:
            is_reverse = False
            return is_reverse
    else:
        print(f"[Error] Invalid mode code: {mode}.")
        return None