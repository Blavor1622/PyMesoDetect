from PIL import Image, ImageDraw
from MesoDetect.ReadData import utils
from MesoDetect.Preprocess.RadarDenoise import dependencies, consts
from MesoDetect.ReadData.utils import gray_value_interval
"""
crossed echo groups:
    1. small groups:
        surrounding shear analysis
    2. large groups:
        folding analysis
    Set a high threshold for folded echo checking
    And first use calculate average layer gap of the whole group echoes for folded echoes detection
        if exceed, then unfold echo
    Then calculate surrounding shear of the echo group
        if not exceed, then draw the echo group    
    
"""
def integrate_velocity_mode(neg_img, pos_img, debug_result_folder=""):
    """
    Integrate neg and pos velocity mode denoise result image into complete radar image
    Args:
        neg_img: PIL Image object of neg denoise image
        pos_img: PIL Image object of pos denoise image
        debug_result_folder: folder path for containing debug result image

    Returns:
    PIL Image object of integrated image
    """
    # Create a integration result image
    integrate_img = Image.new("RGB", neg_img.size, (0, 0, 0))

   # Draw separate echoes and get crossed echo groups
    crossed_groups, refer_img = get_crossed_echo_groups(neg_img, pos_img, integrate_img, debug_result_folder)

    integrate_draw = ImageDraw.Draw(integrate_img)
    # Debug image for surrounding analysis
    surrounding_debug_img = Image.new("RGB", neg_img.size, (0, 0, 0))
    surrounding_debug_draw = ImageDraw.Draw(surrounding_debug_img)

    # Iterate each group and check the surroundings
    radar_zone = utils.get_radar_info("radar_zone")
    cv_pairs = utils.get_color_bar_info("color_velocity_pairs")
    pos_unfold_idx = len(cv_pairs) - 1
    surrounding_offsets = utils.surrounding_offsets
    for crossed_group in crossed_groups:
        # Get unrepeated surroundings
        surrounding_coords = set()
        for echo_coordinate in crossed_group:
            for offset in surrounding_offsets:
                # Get neighbour coordinate with offset
                neighbour_coordinate = (echo_coordinate[0] + offset[0], echo_coordinate[1] + offset[1])
                # Get neighbour value
                neighbour_value = refer_img.getpixel(neighbour_coordinate)
                neighbour_index = round(neighbour_value[0] / gray_value_interval) - 1
                # Surrounding check
                if neighbour_index == -1:
                    if neighbour_coordinate not in surrounding_coords:
                        surrounding_coords.add(neighbour_coordinate)
        if len(surrounding_coords) == 0:
            # Skip empty surroundings crossed echo group
            continue
        # Just need to get surroundings in one single velocity mode image, by default use neg img
        # The surrounding set in the following process need to be only outer surroundings,
        # that is not including inned holes surrounding points,
        # and holes here refer to echo color that is not full RGB channel color
        # But the given denoise image have been filled for those
        # that channel one value not equal to channel two value
        valid_surroundings = []
        for coord in surrounding_coords:
            # Get pixel value from neg image
            surrounding_value = neg_img.getpixel(coord)
            # Calculate index value
            surrounding_index = round(surrounding_value[0] / gray_value_interval) - 1
            if surrounding_index >= 0:
                valid_surroundings.append(surrounding_index)
        # Calculate valid surrounding ratio
        neg_surrounded_ratio = len(valid_surroundings) / len(surrounding_coords)
        # Check ratio to decide keep whose echo
        if neg_surrounded_ratio >= consts.CROSSED_ECHOES_INCLUSION_CHECK_THRESHOLD:
            # Indicates that current group is going to add upon neg velocity mode echoes
            # Draw above echo group
            for coord in crossed_group:
                pos_pixel_value = pos_img.getpixel(coord)
                integrate_draw.point(coord, pos_pixel_value)
                surrounding_debug_draw.point(coord, pos_pixel_value)
            # Execute folded echoes check and cover folded echoes if exceed threshold
            total_gap_sum = 0
            # Calculate average layer gap of the crossed echo
            for coord in crossed_group:
                # Get pixel value
                neg_pixel_value = neg_img.getpixel(coord)
                pos_pixel_value = pos_img.getpixel(coord)
                # Calculate value index
                neg_pixel_index = round(neg_pixel_value[0] / gray_value_interval) - 1
                pos_pixel_index = round(pos_pixel_value[0] / gray_value_interval) - 1
                # Calculate distance
                layer_gap = pos_pixel_index - neg_pixel_index
                total_gap_sum += layer_gap
            avg_layer_gap = total_gap_sum / len(crossed_group)
            if avg_layer_gap >= consts.FOLDED_ECHO_CHECK_THRESHOLD:
                # Indicate that current group is folded and on neg basemaps
                for coord in crossed_group:
                    neg_pixel_value = (0 + 1) * gray_value_interval
                    neg_pixel_color = (neg_pixel_value, 0, neg_pixel_value)
                    integrate_draw.point(coord, neg_pixel_color)
                    surrounding_debug_draw.point(coord, neg_pixel_color)
                continue
            # When the crossed echo group does not folded echoes
            # Then check surrounding shear for small group, while large group is trustful and skip analysis
            if len(crossed_group) < consts.SMALL_GROUP_SIZE_THRESHOLD:
                # First get outer echo list
                group_outer_scopes = []
                for group_coord in crossed_group:
                    # Check each neighbour for the current group coordinate
                    for offset in surrounding_offsets:
                        neighbour_coord = (group_coord[0] + offset[0], group_coord[1] + offset[1])
                        if neighbour_coord not in crossed_group:
                            # Indicate that current group coord is outer scope echo
                            group_outer_scopes.append(group_coord)
                            break
                # Iterate through outer scope echoes to calculate average layer shear
                group_layer_gap_sum = 0
                for outer_coord in group_outer_scopes:
                    # Get current outer point value index
                    outer_value = integrate_img.getpixel(outer_coord)
                    outer_index = round(outer_value[0] / gray_value_interval) - 1
                    outer_layer_gap_sum = 0
                    outer_layer_gap_num = 0
                    # Get neighbour coord for current outer coordinate
                    for offset in surrounding_offsets:
                        neighbour_coord = (outer_coord[0] + offset[0], outer_coord[1] + offset[1])
                        # Filter out group coordinate
                        if neighbour_coord in crossed_group:
                            continue
                        neighbour_value = integrate_img.getpixel(neighbour_coord)
                        neighbour_index = round(neighbour_value[0] / gray_value_interval) - 1
                        if neighbour_index >= 0:
                            outer_layer_gap_sum += abs(outer_index - neighbour_index)
                            outer_layer_gap_num += 1
                    # Calculate average outer layer gap
                    if outer_layer_gap_num > 0:
                        outer_layer_gap_avg = outer_layer_gap_sum / outer_layer_gap_num
                    else:
                        outer_layer_gap_avg = 0
                    group_layer_gap_sum += outer_layer_gap_avg
                # Calculate average group layer gap
                if len(group_outer_scopes) > 0:
                    group_layer_gap_avg = group_layer_gap_sum / len(group_outer_scopes)
                else:
                    group_layer_gap_avg = 0
                if group_layer_gap_avg > consts.CROSSED_SMALL_GROUP_SURROUNDING_GAP_THRESHOLD:
                    for coord in crossed_group:
                        echo_value = neg_img.getpixel(coord)
                        integrate_draw.point(coord, echo_value)
                        surrounding_debug_draw.point(coord, echo_value)
        else:
            # Indicates that current group is going to add upon pos velocity mode echoes
            # Draw above echo group
            for coord in crossed_group:
                neg_pixel_value = neg_img.getpixel(coord)
                integrate_draw.point(coord, neg_pixel_value)
                surrounding_debug_draw.point(coord, neg_pixel_value)
            # Execute folded echoes check and cover folded echoes if exceed threshold
            total_gap_sum = 0
            # Calculate average layer gap of the crossed echo
            for coord in crossed_group:
                # Get pixel value
                neg_pixel_value = neg_img.getpixel(coord)
                pos_pixel_value = pos_img.getpixel(coord)
                # Calculate value index
                neg_pixel_index = round(neg_pixel_value[0] / gray_value_interval) - 1
                pos_pixel_index = round(pos_pixel_value[0] / gray_value_interval) - 1
                # Calculate distance
                layer_gap = pos_pixel_index - neg_pixel_index
                total_gap_sum += layer_gap
            avg_layer_gap = total_gap_sum / len(crossed_group)
            if avg_layer_gap >= consts.FOLDED_ECHO_CHECK_THRESHOLD:
                # Indicate that current group is folded and on neg basemaps
                for coord in crossed_group:
                    pos_pixel_value = (pos_unfold_idx + 1) * gray_value_interval
                    pos_pixel_color = (pos_pixel_value, 0, pos_pixel_value)
                    integrate_draw.point(coord, pos_pixel_color)
                    surrounding_debug_draw.point(coord, pos_pixel_color)
                continue
            # When the crossed echo group does not folded echoes
            # Then check surrounding shear for small group, while large group is trustful and skip analysis
            if len(crossed_group) < consts.SMALL_GROUP_SIZE_THRESHOLD:
                # First get outer echo list
                group_outer_scopes = []
                for group_coord in crossed_group:
                    # Check each neighbour for the current group coordinate
                    for offset in surrounding_offsets:
                        neighbour_coord = (group_coord[0] + offset[0], group_coord[1] + offset[1])
                        if neighbour_coord not in crossed_group:
                            # Indicate that current group coord is outer scope echo
                            group_outer_scopes.append(group_coord)
                            break
                # Iterate through outer scope echoes to calculate average layer shear
                group_layer_gap_sum = 0
                for outer_coord in group_outer_scopes:
                    # Get current outer point value index
                    outer_value = integrate_img.getpixel(outer_coord)
                    outer_index = round(outer_value[0] / gray_value_interval) - 1
                    outer_layer_gap_sum = 0
                    outer_layer_gap_num = 0
                    # Get neighbour coord for current outer coordinate
                    for offset in surrounding_offsets:
                        neighbour_coord = (outer_coord[0] + offset[0], outer_coord[1] + offset[1])
                        # Filter out group coordinate
                        if neighbour_coord in crossed_group:
                            continue
                        neighbour_value = integrate_img.getpixel(neighbour_coord)
                        neighbour_index = round(neighbour_value[0] / gray_value_interval) - 1
                        if neighbour_index >= 0:
                            outer_layer_gap_sum += abs(outer_index - neighbour_index)
                            outer_layer_gap_num += 1
                    # Calculate average outer layer gap
                    if outer_layer_gap_num > 0:
                        outer_layer_gap_avg = outer_layer_gap_sum / outer_layer_gap_num
                    else:
                        outer_layer_gap_avg = 0
                    group_layer_gap_sum += outer_layer_gap_avg
                # Calculate average group layer gap
                if len(group_outer_scopes) > 0:
                    group_layer_gap_avg = group_layer_gap_sum / len(group_outer_scopes)
                else:
                    group_layer_gap_avg = 0
                if group_layer_gap_avg > consts.CROSSED_SMALL_GROUP_SURROUNDING_GAP_THRESHOLD:
                    for coord in crossed_group:
                        echo_value = pos_img.getpixel(coord)
                        integrate_draw.point(coord, echo_value)
                        surrounding_debug_draw.point(coord, echo_value)

    surrounding_debug_img.save(debug_result_folder + "surrounding_fill.png")

    return integrate_img


def get_crossed_echo_groups(neg_img, pos_img, integrate_img, debug_result_folder=""):
    integrate_draw = ImageDraw.Draw(integrate_img)
    # Iterate through both neg and pos image to get uncrossed echoes
    radar_zone = utils.get_radar_info("radar_zone")
    crossed_echoes = []
    for x in range(radar_zone[0], radar_zone[1]):
        for y in range(radar_zone[0], radar_zone[1]):
            # Get pixel value for both neg and pos image
            neg_pixel_value = neg_img.getpixel((x, y))
            pos_pixel_value = pos_img.getpixel((x, y))
            # Calculate gray value index of the pixel value
            neg_pixel_index = round(neg_pixel_value[0] / gray_value_interval) - 1
            pos_pixel_index = round(pos_pixel_value[0] / gray_value_interval) - 1
            # Check both index to decide echo get crossed or not
            if neg_pixel_index != -1 and pos_pixel_index == -1:
                integrate_draw.point((x, y), neg_pixel_value)
            elif neg_pixel_index == -1 and pos_pixel_index != -1:
                integrate_draw.point((x, y), pos_pixel_value)
            elif neg_pixel_index != -1 and pos_pixel_index != -1:
                crossed_echoes.append((x, y))

    # Create a refer image for crossed echo grouping
    refer_img = Image.new("RGB", neg_img.size, (0, 0, 0))
    refer_draw = ImageDraw.Draw(refer_img)
    for echo_coordinate in crossed_echoes:
        refer_draw.point(echo_coordinate, consts.REFER_IMG_COLOR)
    refer_img.save(debug_result_folder + "crossed_refer.png")

    # Get crossed echo groups
    crossed_groups = dependencies.get_echo_groups(refer_img, crossed_echoes)

    return crossed_groups, refer_img

