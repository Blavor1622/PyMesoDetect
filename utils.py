from colorama import Fore, Style
from PIL import Image, ImageDraw
import yaml
import basis
import os


valid_image_extensions = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}
surrounding_offsets = [(0, -1), (0, 1), (-1, 0), (1, 0)]
need_cover_station = ["Z9755", "Z9762", "Z9763"]
gray_value_interval = 17
base_images_path = "base/"


def get_half_color_bar(mode):
    # Load YAML file
    with open(basis.CONFIG_FILE, "r") as file:
        data = yaml.safe_load(file)

    half_len = int(len(data["color_velocity_pairs"]) / 2)
    if mode == 'neg':
        neg_color_scales = []
        for idx in range(half_len - 1, -1, -1):
            neg_color_scales.append(tuple(data["color_velocity_pairs"][idx][0]))
        return neg_color_scales
    elif mode == 'pos':
        pos_color_scales = []
        for idx in range(half_len, len(data["color_velocity_pairs"])):
            pos_color_scales.append(tuple(data["color_velocity_pairs"][idx][0]))
        return pos_color_scales
    else:
        print(Fore.RED + f"[Error] Invalid mode code: `{mode}` for `get_half_color_bar`." + Style.RESET_ALL)
        return


def get_radar_info(var_name):
    # Load YAML file
    with open(basis.CONFIG_FILE, "r") as file:
        data = yaml.safe_load(file)

    if var_name == "image_size":
        return tuple(data["image_size"])
    elif var_name == "radar_zone":
        return data["radar_zone"]
    elif var_name == "radar_center":
        return data["radar_center"]
    elif var_name == "center_diameter":
        return data["center_diameter"]
    elif var_name == "zone_diameter":
        return data["zone_diameter"]
    else:
        print(Fore.RED + f'[Error] Invalid var_name `{var_name}` for `get_radar_info`.' + Style.RESET_ALL)
        return


def get_color_bar_info(var_name):
    # Load YAML file
    with open(basis.CONFIG_FILE, "r") as file:
        data = yaml.safe_load(file)

    if var_name == "color_velocity_pairs":
        cv_pairs_tuple = []
        for cv in data["color_velocity_pairs"]:
            cv_pairs_tuple.append((tuple(cv[0]), cv[1]))
        return cv_pairs_tuple
    else:
        print(Fore.RED + f'[Error] Invalid var_name `{var_name}` for `get_color_bar_info`.' + Style.RESET_ALL)
        return


def get_threshold(var_name):
    # Load YAML file
    with open(basis.CONFIG_FILE, "r") as file:
        data = yaml.safe_load(file)

    if var_name == "blur_threshold":
        return data["blur_threshold"]
    elif var_name == "area_fill_threshold":
        return data["area_fill_threshold"]
    elif var_name == "narrow_fill_threshold":
        return data["narrow_fill_threshold"]
    elif var_name == "complex_fill_threshold":
        return data["complex_fill_threshold"]
    else:
        print(Fore.RED + f'[Error] Invalid var_name `{var_name}` for `get_threshold`.' + Style.RESET_ALL)
        return


def visualize_result(folder_path, gray_img_path, result_name):
    """
    Turning gray image into original radar image for visualization the preprocess result.
    :param folder_path: path of result folder
    :param gray_img_path: path of gray image
    :param result_name: name of visualized result image
    :return: path of visualization result image
    """
    # Check result path
    visualize_result_path = folder_path + "visualization/"
    if not os.path.exists(visualize_result_path):
        os.makedirs(visualize_result_path)

    # Load gray image into PIL Image object
    gray_img = Image.open(gray_img_path)

    # Create visualization result image
    visual_img = Image.new("RGB", gray_img.size, (0, 0, 0))
    visual_draw = ImageDraw.Draw(visual_img)

    # Iterate gray image
    radar_zone = get_radar_info("radar_zone")
    cv_pairs = get_color_bar_info("color_velocity_pairs")
    for x in range(radar_zone[0], radar_zone[1]):
        for y in range(radar_zone[0], radar_zone[1]):
            # Get current pixel value
            pixel_value = gray_img.getpixel((x, y))[0]
            # Calculate gray value index
            gray_value_index = round(1.0 * pixel_value / gray_value_interval) - 1
            # Get actual color and draw
            if 0 <= gray_value_index <= len(cv_pairs) - 1:
                visual_draw.point((x, y), cv_pairs[gray_value_index][0])

    # Save visualization result image
    visualization_result_path = visualize_result_path + result_name + ".png"
    visual_img.save(visualization_result_path)

    return visualization_result_path


def velocity_mode_division(folder_path, gray_img_path):
    # Check result path
    visualize_result_path = folder_path + "visualization/"
    if not os.path.exists(visualize_result_path):
        os.makedirs(visualize_result_path)
    # Load filled image
    fill_img = Image.open(gray_img_path)
    # Create result images
    neg_img = Image.new("RGB", fill_img.size, (0, 0, 0))
    pos_img = Image.new("RGB", fill_img.size, (0, 0, 0))
    neg_draw = ImageDraw.Draw(neg_img)
    pos_draw = ImageDraw.Draw(pos_img)
    # Get basic data
    radar_zone = get_radar_info("radar_zone")
    cv_pairs = get_color_bar_info("color_velocity_pairs")
    base_index = round(len(cv_pairs) / 2) - 1
    for x in range(radar_zone[0], radar_zone[1]):
        for y in range(radar_zone[0], radar_zone[1]):
            pixel_value = fill_img.getpixel((x, y))[0]
            pixel_index = round(1.0 * pixel_value / gray_value_interval) - 1
            if pixel_index >= 0:
                if pixel_index <= base_index:
                    neg_draw.point((x, y), cv_pairs[pixel_index][0])
                else:
                    pos_draw.point((x, y), cv_pairs[pixel_index][0])
    # Save result images
    neg_img.save(visualize_result_path + "neg_filled.png")
    pos_img.save(visualize_result_path + "pos_filled.png")


if __name__ == '__main__':
    # Print values to verify
    print("Radar size:", get_radar_info("image_size"))
    print("Radar Center:", get_radar_info("radar_center"))
    print("Center Diameter:", get_radar_info("center_diameter"))
    print("Radar Zone:", get_radar_info("radar_zone"))
    print("Zone Diameter:", get_radar_info("zone_diameter"))
    print("Color-Velocity Pairs:", get_color_bar_info("color_velocity_pairs"))
    print("Blur Threshold:", get_threshold("blur_threshold"))
    print("Area Fill Threshold:", get_threshold("area_fill_threshold"))
    print("Narrow Fill Threshold:", get_threshold("narrow_fill_threshold"))

    print("neg_color_scales: ",get_half_color_bar("neg"))
    print("pos_color_scales: ",get_half_color_bar("pos"))

