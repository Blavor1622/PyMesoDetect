import numpy as np
from sklearn.decomposition import PCA
from MesoDetect.DataIO.consts import GRAY_SCALE_UNIT, SURROUNDING_OFFSETS
from MesoDetect.ImmerseSimulation.consts import (AREA_MAXIMUM_THRESHOLD, AREA_MINIMUM_THRESHOLD,
                                                 AVG_VOLUME_MINIMUM_THRESHOLD, NARROW_MAXIMUM_THRESHOLD,
                                                 DENSITY_MAXIMUM_THRESHOLD, LAYER_GROUP_MAXIMUM_THRESHOLD)
from MesoDetect.RadarDenoise.dependencies import get_echo_groups


def check_region_attributes(echo_group, refer_img, layer_model_len):
    """
        Check given echo group fulfill the extrema region attribution constraints or not.
    Args:
        echo_group: list of echo coordinates that belongs to a connected component of echos
        refer_img: the image that contains the next-to relationship of echo coordinates in echo_group
        layer_model_len: len of layer model, also equal to the len of radar velocity color legend

    Returns:
        True if the given echo group fulfills the constraints, False otherwise.
    """
    # Check velocity mode of the group
    if len(echo_group) == 0:
        return False
    # Calculate velocity mode of the group
    group_instance = echo_group[0]
    group_instance_value = refer_img.getpixel(group_instance)
    group_instance_index = round(group_instance_value[0] / GRAY_SCALE_UNIT) - 1
    half_len = round(layer_model_len / 2)
    if group_instance_index <= half_len - 1:
        is_neg = True
    else:
        is_neg = False

    # Get area of the group
    area = len(echo_group)
    if not AREA_MINIMUM_THRESHOLD <= area <= AREA_MAXIMUM_THRESHOLD:
        return False

    # Calculate the average volume of the group
    volume = 0
    for echo_coord in echo_group:
        echo_value = refer_img.getpixel(echo_coord)
        echo_index = round(echo_value[0] / GRAY_SCALE_UNIT) - 1
        if is_neg:
            volume += half_len - echo_index
        else:
            volume += echo_index - half_len + 1
    vav = volume / area
    if not vav >= AVG_VOLUME_MINIMUM_THRESHOLD:
        return False

    # Get narrow degree of the group using PCA when group size bigger than 2
    if area >= 2:
        points_np = np.array(echo_group)
        pca = PCA(n_components=2)
        pca.fit(points_np)
        projected = pca.transform(points_np)
        length = projected[:, 0].max() - projected[:, 0].min()
        width = projected[:, 1].max() - projected[:, 1].min()
        if width == 0:
            narrow_degree =float('inf')
        else:
            narrow_degree = length / width
    else:
        narrow_degree = 1
    if not narrow_degree <= NARROW_MAXIMUM_THRESHOLD:
        return False

    # Calculate density degree
    # First calculate the perimeter
    surroundings = set()
    for echo_coord in echo_group:
        # Check neighbour for each pixel
        for offset in SURROUNDING_OFFSETS:
            neighbour_coord = (echo_coord[0] + offset[0], echo_coord[1] + offset[1])
            # Filter out inner pixel
            if neighbour_coord not in echo_group:
                if neighbour_coord not in surroundings:
                    surroundings.add(neighbour_coord)
    # Note that the perimeter here calculated is the outer range of the group
    perimeter = len(surroundings)
    if area == 0:
        density_degree = float("inf")
    else:
        density_degree = perimeter ** 2 / area
    if not density_degree <= DENSITY_MAXIMUM_THRESHOLD:
        return False

    # Check echo complexity
    group_layer_model = []
    for layer_idx in range(layer_model_len):
        group_layer_model.append([])
    # Get group layer model
    for echo_coord in echo_group:
        # Get pixel value
        echo_value = refer_img.getpixel(echo_coord)
        echo_index = round(echo_value[0] / GRAY_SCALE_UNIT) - 1
        if echo_index in range(layer_model_len):
            group_layer_model[echo_index].append(echo_coord)
    # Group each layer
    group_layer_groups = []
    valid_layer_num = 0
    total_group_count = 0
    for layer_idx in range(layer_model_len):
        # Skip empty layer
        if len(group_layer_model[layer_idx]) == 0:
            continue
        valid_layer_num += 1
        current_layer_groups = get_echo_groups(refer_img, group_layer_model[layer_idx])
        total_group_count += len(current_layer_groups)
    # Calculate average group num in each layer
    if valid_layer_num == 0:
        avg_layer_group_num = float("inf")
    else:
        avg_layer_group_num = total_group_count / valid_layer_num
    if not avg_layer_group_num <= LAYER_GROUP_MAXIMUM_THRESHOLD:
        return False
    else:
        return True
