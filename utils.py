from colorama import Fore, Style
import yaml
import basis

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
    print("Complex Fill Threshold:", get_threshold("complex_fill_threshold"))

    print("neg_color_scales: ",get_half_color_bar("neg"))
    print("pos_color_scales: ",get_half_color_bar("pos"))

