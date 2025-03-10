from PIL import Image,ImageDraw
import utils
import os
from colorama import Fore, Style


def get_gray_img(rlt_folder_path, mode):
    """
    Generating gray image for latter process according to the mode code
    :param rlt_folder_path: the path of result image folder
    :param mode: a string that only have value of "neg" or "pos"
    :return: path of gray image
    """
    # Get color bar according to the mode code
    if mode == "neg":
        color_bar = utils.get_half_color_bar("neg")
    elif mode == "pos":
        color_bar = utils.get_half_color_bar("pos")
    else:
        print(Fore.RED + f"[Error] Invalid mode code: {mode} for `get_gray_img`." + Style.RESET_ALL)
        return

    # Check result folder existence
    if not os.path.exists(rlt_folder_path + '/sink/'):
        os.makedirs(rlt_folder_path + '/sink/')

    # Open filled image
    filled_img = Image.open(rlt_folder_path + '/blur/rm_filled.png')

    # Create blank image for drawing result
    image_size = utils.get_radar_info("image_size")
    gray_img = Image.new("RGB", (image_size[1], image_size[1]), (255, 255, 255))
    gray_draw = ImageDraw.Draw(gray_img)

    # Iterate the filled image for drawing the gray image
    radar_zone = utils.get_radar_info("radar_zone")
    for x in range(radar_zone[0], radar_zone[1]):
        for y in range(radar_zone[0], radar_zone[1]):
            # Get current pixel value
            pixel_value = filled_img.getpixel((x, y))
            for idx in range(len(color_bar)):
                if utils.is_color_equal(pixel_value, color_bar[idx], 10):
                    gray_value = (len(color_bar) - idx - 1) * 30
                    gray_draw.point((x, y), (gray_value, gray_value, gray_value))
                    break

    # Save result image
    rlt_path = rlt_folder_path + '/sink/' + mode + "_gray.png"
    gray_img.save(rlt_path)

    return rlt_path