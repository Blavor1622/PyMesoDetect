from PIL import Image, ImageDraw
import utils
from Preprocess.RadarDenoise import dependencies
from Preprocess.RadarDenoise import consts


def unfold_echoes(integrated_img, debug_result_folder=""):
    """

    Args:
        integrated_img:
        debug_result_folder:

    Returns:

    """
    # Get layer model of integrated image
    layer_model = dependencies.get_layer_model(integrated_img)
    # Get basic data
    gray_value_interval = utils.gray_value_interval
    half_index = round(len(layer_model) / 2) - 1
    surrounding_offsets = utils.surrounding_offsets
    # Create a image for the unfolding result
    # Note that using copy to separate the tow mode process in case of interference
    unfold_img = integrated_img.copy()
    unfold_draw = ImageDraw.Draw(unfold_img)

    # Debug image
    debug_img = Image.new("RGB", integrated_img.size, (0, 0, 0))
    debug_draw = ImageDraw.Draw(debug_img)

    # Unfold process for neg mode
    neg_target_indexes = range(len(layer_model) - consts.FOLDED_LAYER_NUM, len(layer_model))
    unfolded_value = (0 + 1) * gray_value_interval
    unfolded_color = (unfolded_value, unfolded_value, unfolded_value)
    for neg_tar_idx in neg_target_indexes:
        # Get echo groups of current target echoes
        echo_groups = dependencies.get_echo_groups(integrated_img, layer_model[neg_tar_idx])
        # Analise each group's surrounding
        for echo_group in echo_groups:
            surroundings = set()
            valid_surrounding_indexes = []
            opposite_mode_indexes = []
            for coord in echo_group:
                for offset in surrounding_offsets:
                    neighbour_coord = (coord[0] + offset[0], coord[1] + offset[1])
                    neighbour_value = integrated_img.getpixel(neighbour_coord)
                    neighbour_index = round(neighbour_value[0] / gray_value_interval) - 1
                    if neighbour_index != neg_tar_idx:
                        if neighbour_coord not in surroundings:
                            surroundings.add(neighbour_coord)
                            if neighbour_index >= 0:
                                valid_surrounding_indexes.append(neighbour_index)
                                if neighbour_index <= half_index:
                                    opposite_mode_indexes.append(neighbour_index)

            if (len(valid_surrounding_indexes) > 0
                and len(valid_surrounding_indexes) == len(opposite_mode_indexes)):
                # Indicate that current echo groups only has opposite echo surroundings
                # Check surrounding threshold
                opposite_surrounded_ratio = len(opposite_mode_indexes) / len(surroundings)
                if opposite_surrounded_ratio >= consts.OPPOSITE_SURROUNDED_THRESHOLD:
                    for coord in echo_group:
                        unfold_draw.point(coord, unfolded_color)
                        debug_draw.point(coord, (0, 0, 255))
    # Unfold process for pos mode
    pos_target_indexes = range(0 + consts.FOLDED_LAYER_NUM - 1, -1, -1)
    unfolded_value = (len(layer_model) - 1 + 1) * gray_value_interval
    unfolded_color = (unfolded_value, unfolded_value, unfolded_value)
    for pos_tar_idx in pos_target_indexes:
        # Get echo groups of current target echoes
        echo_groups = dependencies.get_echo_groups(integrated_img, layer_model[pos_tar_idx])
        # Analise each group's surrounding
        for echo_group in echo_groups:
            surroundings = set()
            valid_surrounding_indexes = []
            opposite_mode_indexes = []
            for coord in echo_group:
                for offset in surrounding_offsets:
                    neighbour_coord = (coord[0] + offset[0], coord[1] + offset[1])
                    neighbour_value = integrated_img.getpixel(neighbour_coord)
                    neighbour_index = round(neighbour_value[0] / gray_value_interval) - 1
                    if neighbour_index != pos_tar_idx:
                        if neighbour_coord not in surroundings:
                            surroundings.add(neighbour_coord)
                            if neighbour_index >= 0:
                                valid_surrounding_indexes.append(neighbour_index)
                                if neighbour_index >= half_index + 1:
                                    opposite_mode_indexes.append(neighbour_index)

            if (len(valid_surrounding_indexes) > 0
                    and len(valid_surrounding_indexes) == len(opposite_mode_indexes)):
                # Indicate that current echo groups only has opposite echo surroundings
                # Check surrounding threshold
                opposite_surrounded_ratio = len(opposite_mode_indexes) / len(surroundings)
                if opposite_surrounded_ratio >= consts.OPPOSITE_SURROUNDED_THRESHOLD:
                    for coord in echo_group:
                        unfold_draw.point(coord, unfolded_color)
                        debug_draw.point(coord, (255, 0, 0))
    # Save debug image
    debug_img.save(debug_result_folder + "unfold_debug.png")
    return unfold_img

