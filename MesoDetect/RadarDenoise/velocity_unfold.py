from PIL import Image, ImageDraw
from MesoDetect.RadarDenoise import dependencies, consts
from MesoDetect.DataIO.consts import GRAY_SCALE_UNIT, SURROUNDING_OFFSETS


def unfold_echoes(integrated_img, enable_debug, debug_result_folder=""):
    """

    Args:
        integrated_img:
        enable_debug:
        debug_result_folder:

    Returns:

    """
    # Get layer model of integrated image
    layer_model = dependencies.get_layer_model(integrated_img)

    # Note that using copy to separate the tow mode process in case of interference
    unfold_img = integrated_img.copy()

    # Neg unfolding
    unfold_img = folded_echo_analysis(layer_model, integrated_img, unfold_img, "neg", enable_debug, debug_result_folder)

    # Pos unfolding
    unfold_img = folded_echo_analysis(layer_model, integrated_img, unfold_img, "pos", enable_debug, debug_result_folder)

    return unfold_img


def folded_echo_analysis(layer_model, integrated_img, unfold_img, mode, enable_debug, debug_result_folder=""):
    # Check mode code
    if mode == "neg":
        target_indexes = range(len(layer_model) - consts.FOLDED_LAYER_NUM, len(layer_model))
        unfolded_value = (0 + 1) * GRAY_SCALE_UNIT
        unfolded_color = (unfolded_value, unfolded_value, unfolded_value)
        is_reversed = False
    elif mode == "pos":
        target_indexes = range(0 + consts.FOLDED_LAYER_NUM - 1, -1, -1)
        unfolded_value = (len(layer_model) - 1 + 1) * GRAY_SCALE_UNIT
        unfolded_color = (unfolded_value, unfolded_value, unfolded_value)
        is_reversed = True
    else:
        print("Error")
        return

    # Get basic data
    half_index = round(len(layer_model) / 2) - 1

    # Debug image
    debug_img = Image.new("RGB", integrated_img.size, (0, 0, 0))
    debug_draw = ImageDraw.Draw(debug_img)

    # Get refer image for target echoes grouping
    refer_img = Image.new("RGB", integrated_img.size, (0, 0, 0))
    refer_draw = ImageDraw.Draw(refer_img)
    # Get refer image color
    refer_img_color = consts.REFER_IMG_COLOR

    unfold_draw = ImageDraw.Draw(unfold_img)
    target_echo_list = []
    for layer_idx in target_indexes:
        for echo_coord in layer_model[layer_idx]:
            target_echo_list.append(echo_coord)
            refer_draw.point(echo_coord, refer_img_color)

    # Get target echo groups
    target_echo_groups = dependencies.get_echo_groups(refer_img, target_echo_list)

    # Analise each target echo group
    for echo_group in target_echo_groups:
        surroundings = set()
        valid_surrounding_indexes = []
        opposite_mode_indexes = []
        for coord in echo_group:
            for offset in SURROUNDING_OFFSETS:
                neighbour_coord = (coord[0] + offset[0], coord[1] + offset[1])
                # Extract current pixel color from refer image to decide whether is surrounding or not
                neighbour_refer_value = refer_img.getpixel(neighbour_coord)
                neighbour_refer_index = round(neighbour_refer_value[0] / GRAY_SCALE_UNIT) - 1
                if neighbour_refer_index == -1:
                    # Indicate that current neighbour pixel is not in the group
                    if neighbour_coord not in surroundings:
                        surroundings.add(neighbour_coord)
                        neighbour_value = integrated_img.getpixel(neighbour_coord)
                        neighbour_index = round(neighbour_value[0] / GRAY_SCALE_UNIT) - 1
                        if neighbour_index >= 0:
                            valid_surrounding_indexes.append(neighbour_index)
                            if not is_reversed and neighbour_index <= half_index:
                                opposite_mode_indexes.append(neighbour_index)
                            elif is_reversed and neighbour_index >= half_index + 1:
                                opposite_mode_indexes.append(neighbour_index)
        if len(valid_surrounding_indexes) > 0:
            # Indicates that current echo groups is not isolated
            # Calculate opposite echoes compose how much in valid echoes
            opposite_compose_ratio = len(opposite_mode_indexes) / len(valid_surrounding_indexes)
            if opposite_compose_ratio >= consts.OPPOSITE_COMPOSE_THRESHOLD:
                # Indicate that current echo groups only has opposite echo surroundings
                # Check surrounding threshold
                opposite_surrounded_ratio = len(opposite_mode_indexes) / len(surroundings)
                if opposite_surrounded_ratio >= consts.OPPOSITE_SURROUNDED_THRESHOLD:
                    for coord in echo_group:
                        unfold_draw.point(coord, unfolded_color)
                        debug_draw.point(coord, (0, 255, 0))

    # Save debug image
    if enable_debug:
        debug_img.save(debug_result_folder + mode + "_unfold_debug.png")
        unfold_img_path = debug_result_folder + "unfold.png"
        unfold_img.save(unfold_img_path)

    return unfold_img
