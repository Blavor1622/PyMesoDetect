from PIL import Image
import numpy as np
from skimage.segmentation import flood_fill
from MesoDetect.DataIO.radar_config import get_radar_info, get_color_bar_info
from MesoDetect.DataIO.consts import GRAY_SCALE_UNIT, SURROUNDING_OFFSETS


"""
    Internal Dependency Functions
"""
def get_layer_model(filled_img):
    """
    Generate a list of same velocity echo coordinate lists that have same length and according index
    value with the color velocity pairs
    :param filled_img: Pillow Image object of filled image
    :return: layer model
    """
    # Get dependency data
    radar_zone = get_radar_info("radar_zone")
    cv_pairs = get_color_bar_info("color_velocity_pairs")
    gray_value_interval = GRAY_SCALE_UNIT

    # Construct empty data structure
    layer_model = []
    for idx in range(len(cv_pairs)):
        layer_model.append([])

    # iterate the filled image
    for x in range(radar_zone[0], radar_zone[1]):
        for y in range(radar_zone[0], radar_zone[1]):
            # get current pixel value
            pixel_value = filled_img.getpixel((x, y))
            gray_index = round(pixel_value[0] * 1.0 / gray_value_interval) - 1

            if -1 < gray_index < len(cv_pairs):
                layer_model[gray_index].append((x, y))

    return layer_model


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
    # get neighbour coordinate offset
    neighbour_offsets = SURROUNDING_OFFSETS

    # Get radar zone
    radar_zone = get_radar_info("radar_zone")
    gray_value_interval = GRAY_SCALE_UNIT

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
                    # radar scale check
                    if (radar_zone[0] <= neighbour[0] <= radar_zone[1]
                            and radar_zone[0] <= neighbour[1] <= radar_zone[1]):
                        neighbour_value = refer_img.getpixel(neighbour)[0]
                        if round(neighbour_value * 1.0 / gray_value_interval) - 1 == target_index:
                            # Mean that neighbour value similar to target value (slight difference is allowed)
                            if neighbour not in visited:
                                visited.add(neighbour)
                                component.append(neighbour)
                                stack.append(neighbour)
            components.append(component)
    return components


def inner_filling(refer_img, fill_color, fill_img):
    """
    Flooding outer blanks in given gray image and fill inner blanks of the image with
    gray color that gray value index indicates
    :param refer_img: PIL Image object in RGB mode with gray color that indicating inner relationship
    :param fill_color: RGB color for filling
    :param fill_img: PIL IMage object in RGB mode that need inner filling
    :return: a PIL Image object of an inner filled gray image
    """
    # Check valid fill color
    if len(fill_color) != 3:
        print(f"[Error] Invalid fill color: {fill_color} for `inner_filling`.")
        return None
    # Get basic data
    gray_value_interval = GRAY_SCALE_UNIT
    radar_zone = get_radar_info("radar_zone")

    # Convert RGB Image into gray image numpy array
    gray_img_arr = np.array(refer_img.convert("L"))

    # flood fill the array from point (0, 0) with value 255
    flooded_arr = flood_fill(gray_img_arr, (0, 0), new_value=255, connectivity=1)

    # Get interested zone border of the image
    top, left = radar_zone[0], radar_zone[0]
    bottom, right = radar_zone[1], radar_zone[1]

    # Convert original gray RGB PIL image into numpy array
    frame_arr = np.array(fill_img)

    # Extract radar zone from the array
    flooded_arr_sub = flooded_arr[top:bottom, left:right]  # shape: (subH, subW)
    frame_arr_sub = frame_arr[top:bottom, left:right, :]  # shape: (subH, subW, 3)

    # Compute the gray color index in one shot
    color_index_arr = np.round(flooded_arr_sub.astype(float) / gray_value_interval) - 1

    # Identify pixels where the index == -1
    mask = (color_index_arr == -1)

    # Fill those pixels in the frame_sub
    frame_arr_sub[mask] = [fill_color[0], fill_color[1], fill_color[2]]

    # Convert back to PIL and save
    fill_img = Image.fromarray(frame_arr, mode="RGB")
    return fill_img

