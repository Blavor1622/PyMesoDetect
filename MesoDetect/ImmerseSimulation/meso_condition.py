import numpy as np
from sklearn.decomposition import PCA
from MesoDetect.ReadData.utils import gray_value_interval
from MesoDetect.ReadData.utils import surrounding_offsets
"""
Definition of thresholds: area, narrow degree, average volume and density degree
"""
AREA_MINIMUM_THRESHOLD = 10
AREA_MAXIMUM_THRESHOLD = 135
NARROW_MAXIMUM_THRESHOLD = 4.25
AVG_VOLUME_MINIMUM_THRESHOLD = 2.25
DENSITY_MAXIMUM_THRESHOLD = 75
LAYER_GROUP_MAXIMUM_THRESHOLD = 1.75

neighbour_offsets = [(0, -1), (0, 1), (-1, 0), (1, 0), (-1, -1), (-1, 1), (1, -1), (1, 1)]


def check_group_condition(echo_group, refer_img, layer_model_len):
    # Check velocity mode of the group
    if len(echo_group) == 0:
        return False
    # Calculate velocity mode of the group
    group_instance = echo_group[0]
    group_instance_value = refer_img.getpixel(group_instance)
    group_instance_index = round(group_instance_value[0] / gray_value_interval) - 1
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
        echo_index = round(echo_value[0] / gray_value_interval) - 1
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
        for offset in surrounding_offsets:
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
        echo_index = round(echo_value[0] / gray_value_interval) - 1
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


def get_echo_groups(refer_img, coordinate_list):
    """
    a utility function that divides the given coordinate_list
    and then return a list of connected components
    :param refer_img: a Pillow Image object that used for checking connected relationship of echoes
    :param coordinate_list: list of coordinate that might have several connected component
    :return: a list of connected components
    """
    if len(coordinate_list) == 0:
        return [[]]

    # Extract gray value index of current point
    target_value = refer_img.getpixel(coordinate_list[0])[0]
    target_index = round(1.0 * target_value / gray_value_interval) - 1

    components = []
    visited = set()
    for point in coordinate_list:
        if point not in visited:
            visited.add(point)
            stack = [point]
            component = [point]
            while stack:
                current_point = stack.pop()
                # get surrounding pixel values
                for offset in neighbour_offsets:
                    # ger neighbour pixel coordinate
                    neighbour = (current_point[0] + offset[0], current_point[1] + offset[1])
                    neighbour_value = refer_img.getpixel(neighbour)[0]
                    if round(neighbour_value * 1.0 / gray_value_interval) - 1 == target_index:
                        # Mean that neighbour value similar to target value (slight difference is allowed)
                        if neighbour not in visited:
                            visited.add(neighbour)
                            component.append(neighbour)
                            stack.append(neighbour)
            components.append(component)

    return components