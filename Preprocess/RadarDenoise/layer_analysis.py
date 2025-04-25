from PIL import Image, ImageDraw
import utils
from Preprocess.RadarDenoise import dependencies
from Preprocess.RadarDenoise import consts


def get_denoise_img(fill_img, layer_model, mode, debug_result_folder=""):
    """
    denoise given fill image and return denoised result image
    Args:
        fill_img: PIL Image Object of narrow filled image
        layer_model: list of layer echoes
        mode: string that indicates the velocity mode
        debug_result_folder: debug result folder

    Returns:
    PIL Image object of a denoised image
    """
    # Get base echo image
    denoise_img = get_base_echo_img(layer_model, fill_img.size, mode)
    denoise_img.save(debug_result_folder + mode + "_base.png")

    # Check mode code
    if mode == "neg":
        base_index = round(len(layer_model) / 2) - 1
        layer_range = range(base_index, -1, -1)
        is_reverse = True
    elif mode == "pos":
        base_index = round(len(layer_model) / 2)
        layer_range = range(base_index, len(layer_model))
        is_reverse = False
    else:
        print()
        return

    # Keep echo groups which size exceed size threshold that is more likely to be trustful
    gray_value_interval = utils.gray_value_interval
    denoise_draw = ImageDraw.Draw(denoise_img)
    small_echo_groups = []
    for layer_idx in layer_range:
        # Get echo groups for current layer
        echo_groups = dependencies.get_echo_groups(fill_img, layer_model[layer_idx])
        # Calculate gray color value for current layer
        layer_echo_value = (layer_idx + 1) * gray_value_interval
        echo_color = (layer_echo_value, layer_echo_value, layer_echo_value)
        # Create an inner filling refer image
        inner_fill_refer_img = Image.new("RGB", fill_img.size, (0, 0, 0))
        inner_fill_refer_draw = ImageDraw.Draw(inner_fill_refer_img)
        # Draw echo groups that bigger than size threshold
        for echo_group in echo_groups:
            # Huge echo skip denoise
            if len(echo_group) >= consts.SMALL_GROUP_SIZE_THRESHOLD:
                for echo_coordinate in echo_group:
                    denoise_draw.point(echo_coordinate, echo_color)
                    inner_fill_refer_draw.point(echo_coordinate, echo_color)
            # In the meantime get small echo groups list
            else:
                if len(echo_group) > 0:
                    small_echo_groups.append(echo_group)
        # Execute inner filling for each layer with valid full RGB color
        denoise_img = dependencies.inner_filling(inner_fill_refer_img, echo_color, denoise_img)
        denoise_draw = ImageDraw.Draw(denoise_img)
    # Save debug image
    denoise_img.save(debug_result_folder + mode + "_smooth.png")

    # Small echo groups analysis
    surrounding_offsets = utils.surrounding_offsets
    for small_group in small_echo_groups:
        # Get below echo value of current group
        # There are three cases:
        #   1. valid echo with full RGB color from large group inner filling(velocity >= 0)
        #   2. base echo with two channel RGB color from base echo(velocity 0)
        #   3. empty base
        below_value = denoise_img.getpixel(small_group[0])
        # Calculate below value index using the second channel value
        below_value_index = round(1.0 * below_value[1] / gray_value_interval) - 1

        # Calculate small group actual value index
        current_group_value = fill_img.getpixel(small_group[0])
        current_group_index = round(1.0 * current_group_value[0] / gray_value_interval) - 1
        if below_value_index >= 0:
            # Indicate that current group is above valid echoes
            # Only draw current group when it does not exceed layer index gap
            if not is_reverse and 0 <= current_group_index - below_value_index <= consts.LAYER_GAP_THRESHOLD:
                for echo_coordinate in small_group:
                    denoise_draw.point(echo_coordinate, current_group_value)
            elif is_reverse and 0 <= below_value_index - current_group_index <= consts.LAYER_GAP_THRESHOLD:
                for echo_coordinate in small_group:
                    denoise_draw.point(echo_coordinate, current_group_value)
        else:
            # Indicate that current group is above base echoes or just empty
            base_below_index = round(1.0 * below_value[0] / gray_value_interval) - 1
            if base_below_index >= 0:
                # Indicate that no empty but is base echo
                # Get surroundings
                surroundings = set()
                valid_surroundings = set()
                valid_surrounding_indexes = []
                for echo_coordinate in small_group:
                    # Get valid echo neighbour coordinates
                    for offset in surrounding_offsets:
                        neighbour_coordinate = (echo_coordinate[0] + offset[0], echo_coordinate[1] + offset[1])
                        neighbour_value = denoise_img.getpixel(neighbour_coordinate)[1]
                        neighbour_index = round(neighbour_value / gray_value_interval) - 1
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
                            round_avg_value = (round_avg_index + 1) * gray_value_interval
                            for echo_coordinate in small_group:
                                denoise_draw.point(echo_coordinate, (round_avg_value, round_avg_value, round_avg_value))
                else:
                    # Indicate that current small group has not valid surroundings
                    # Check with base below index
                    if abs(current_group_index - base_below_index) <= consts.LAYER_GAP_THRESHOLD:
                        for echo_coordinate in small_group:
                            denoise_draw.point(echo_coordinate, current_group_value)
            # Groups that above empty is not drawn and is filtered out
    # # Remove small isolated echo that is base on the base echo
    # exclude_base_img = Image.new("RGB", fill_img.size, (0, 0, 0))
    # exclude_base_draw = ImageDraw.Draw(exclude_base_img)
    # radar_zone = utils.get_radar_info("radar_zone")
    # exclude_img_echo_list = []
    # for x in range(radar_zone[0], radar_zone[1]):
    #     for y in range(radar_zone[0], radar_zone[1]):
    #         # Get pixel value from denoise image
    #         pixel_value = denoise_img.getpixel((x, y))
    #         # Calculate value index, use the second channel value for excluding base echo
    #         pixel_index = round(pixel_value[1] / gray_value_interval) - 1
    #         if pixel_index >= 0:
    #             exclude_img_echo_list.append((x, y))
    #             exclude_base_draw.point((x, y), REFER_IMG_COLOR)
    # exclude_base_img.save(debug_result_folder + mode + "_exclude_base.png")
    # # Get echo groups from exclude base image
    # exclude_base_echo_groups = get_echo_groups(exclude_base_img, exclude_img_echo_list)
    #
    # # Check group size for each group
    # denoise_draw = ImageDraw.Draw(denoise_img)
    # for echo_group in exclude_base_echo_groups:
    #     if len(echo_group) < SMALL_GROUP_SIZE_THRESHOLD:
    #         # Remove small isolated groups that smaller than threshold from denoise image
    #         for echo_coord in echo_group:
    #             denoise_draw.point(echo_coord, (0, 0, 0))
    # # Execute inner filling for denoise after exclude base echo isolated echo groups removing
    # base_color_value = (base_index + 1) * gray_value_interval
    # denoise_img = inner_filling(denoise_img, (base_color_value, 0, base_color_value), denoise_img)

    # Filling base echo
    denoise_img = base_echo_fill(denoise_img, len(layer_model), mode)
    return denoise_img


"""
Note: image scale small group and layer scale small group are distinct. 
"""
def get_base_echo_img(layer_model, radar_img_size, mode):
    """
    Generate an inner filled base echo image with two valid channel color
    that has remove image scale small echo groups. This image is useful for latter analysis
    including denoise and velocity unfold
    Args:
        layer_model: list of layer echoes
        radar_img_size: size of radar image
        mode: a string that indicate the velocity mode

    Returns:
        A PIL Image Object of base velocity image
    """
    # Check mode code
    if mode == "neg":
        base_index = round(len(layer_model) / 2) - 1
        layer_range = range(base_index, -1, -1)
    elif mode == "pos":
        base_index = round(len(layer_model) / 2)
        layer_range = range(base_index, len(layer_model))
    else:
        print()
        return

    # Create an empty image
    base_img = Image.new("RGB", radar_img_size, (0, 0, 0))
    base_draw = ImageDraw.Draw(base_img)
    # Get basic values
    gray_value_interval = utils.gray_value_interval
    base_value = gray_value_interval * (base_index + 1)
    # Use two valid channel color to distinguish base echo
    base_color = (base_value, 0, base_value)
    # Iterate each layer for draw all echo as base echo
    for layer_idx in layer_range:
        for echo_coordinate in layer_model[layer_idx]:
            base_draw.point(echo_coordinate, base_color)

    # Execute inner filling which might be useful for velocity unfold
    base_img = dependencies.inner_filling(base_img, base_color, base_img)

    # Get all base echo pixel coordinate
    echo_pixel_list = []
    radar_zone = utils.get_radar_info("radar_zone")
    for x in range(radar_zone[0], radar_zone[1]):
        for y in range(radar_zone[0], radar_zone[1]):
            # Get current pixel value
            pixel_coordinate = (x, y)
            pixel_value = base_img.getpixel(pixel_coordinate)[0]
            # Calculate color value index of the pixel
            pixel_index = round(1.0 * pixel_value / gray_value_interval) - 1
            if pixel_index != -1:
                echo_pixel_list.append(pixel_coordinate)

    # Get base echo groups
    echo_groups = dependencies.get_echo_groups(base_img, echo_pixel_list)

    # Get list of base echo groups that smaller than the size threshold
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


def base_echo_fill(gray_img, layer_model_len, mode):
    """
    Analise all base echo groups and fill them base on the valid surrounding echo values
    when surrounded ratio exceed threshold. The filling color is one valid channel RGB color.
    Args:
        gray_img: gray value image in PIL Image object type that has base echoes
        layer_model_len: len of echo layer list
        mode: string value that indicate the velocity mode

    Returns: a filled image in PIL Image object type

    """
    # Check mode code
    gray_value_interval = utils.gray_value_interval
    if mode == "neg":
        base_index = round(layer_model_len / 2) - 1
    elif mode == "pos":
        base_index = round(layer_model_len / 2)
    else:
        print()
        return
    # get base echo color value
    base_color_value = (base_index + 1) * gray_value_interval
    base_color = (base_color_value, base_color_value, base_color_value)

    # Create a refer image for grouping
    refer_img = Image.new("RGB", gray_img.size, (0, 0, 0))
    refer_draw = ImageDraw.Draw(refer_img)

    # Iterate radar zone to get need fill area
    radar_zone = utils.get_radar_info("radar_zone")
    base_echo_list = []
    for x in range(radar_zone[0], radar_zone[1]):
        for y in range(radar_zone[0], radar_zone[1]):
            # Get current pixel value
            pixel_value = gray_img.getpixel((x, y))
            # Calculate gray value index
            pixel_index_0 = round(pixel_value[0] / gray_value_interval) - 1     # First channel value
            pixel_index_1 = round(pixel_value[1] / gray_value_interval) - 1     # Second channel value
            # Check whether is base echo or not
            if pixel_index_0 != pixel_index_1:
                base_echo_list.append((x, y))
                refer_draw.point((x, y), base_color)

    # Get base echo groups
    base_echo_groups = dependencies.get_echo_groups(refer_img, base_echo_list)
    surrounding_offsets = utils.surrounding_offsets
    # Analise each group's surrounding
    gray_draw = ImageDraw.Draw(gray_img)
    for echo_group in base_echo_groups:
        # First get surrounded valid indexes
        surroundings = set()
        valid_surrounding_indexes = []
        for echo_coordinate in echo_group:
            for offset in surrounding_offsets:
                neighbour_coordinate = (echo_coordinate[0] + offset[0], echo_coordinate[1] + offset[1])
                neighbour_value = gray_img.getpixel(neighbour_coordinate)
                neighbour_index_0 = round(neighbour_value[0] / gray_value_interval) - 1
                neighbour_index_1 = round(neighbour_value[1] / gray_value_interval) - 1
                if neighbour_index_0 == neighbour_index_1:
                    # Indicate that current neighbor is not base echo
                    if neighbour_coordinate not in surroundings:
                        # Note that surroundings set might include empty pixel coord
                        surroundings.add(neighbour_coordinate)
                        if neighbour_index_0 >= 0:
                            # Add valid echo indexes into list
                            valid_surrounding_indexes.append(neighbour_index_0)
        if len(surroundings) == 0:
            continue
        surrounded_ratio = len(valid_surrounding_indexes) / len(surroundings)
        # Fill base echo group with average surrounded valid echo value when exceed surrounded ratio
        if surrounded_ratio >= consts.BASE_ECHO_SURROUNDED_RATIO_THRESHOLD:
            # Calculate average surrounding index
            avg_surrounding_idx = sum(valid_surrounding_indexes) / len(valid_surrounding_indexes)
            round_avg_idx = round(avg_surrounding_idx)
            avg_value = (round_avg_idx + 1) * gray_value_interval
            for echo_coordinate in echo_group:
                # Note that the base filling value is one valid channel RGB color
                gray_draw.point(echo_coordinate, (avg_value, 0, 0))
    return gray_img
