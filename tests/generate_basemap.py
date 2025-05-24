from PIL import Image, ImageDraw
import os

VALID_IMG_EXTENSION = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}

cover_color = (0, 0, 0)
"""
Note that echoes are less possible to appear in same place on radar image across a wide range of time,
while the boundary in radar image is static with same place. Therefore, this can be used to extract the boundary
from several radar images of same station
"""


def is_color_equal(color1, color2, delta):
    """Check if two colors are similar within a given delta."""
    return all(abs(c1 - c2) <= delta for c1, c2 in zip(color1[:3], color2[:3]))


def extract_white_boundary(input_folder, station_num, result_folder):
    """
    Extract white boundary from given radar images of same station, so that latter analysis
    can use the extract result to cover the boundary in radar image in case of boundary color
    meet with echo color, for example (255, 255, 255).
    :param input_folder: path of same station radar image which contains several images
    more images are suggested
    :param station_num: a string of radar station number with format "Zxxxx"
    :param result_folder: path of result folder
    :return: path of extract result
    """
    # Get image names from input folder
    all_files = os.listdir(input_folder)
    image_files = [file for file in all_files if os.path.splitext(file)[1].lower() in VALID_IMG_EXTENSION]

    # Get first radar image
    first_img_path  = input_folder + image_files[0]
    first_img = Image.open(first_img_path)

    # Create result image with same size of first radar image
    result_img = Image.new("RGB", first_img.size, (0, 0, 0))
    result_draw = ImageDraw.Draw(result_img)

    # Analise each radar image
    img_num = 0
    for image_name in image_files:
        print(f"[Info] Iteration {img_num}.")
        img_num += 1
        # Get image entire path
        image_path = input_folder + image_name

        # open image
        radar_img = Image.open(image_path)

        # iterate radar zone to get target pixels
        for x in range(0, radar_img.size[1]):
            for y in range(0, radar_img.size[1]):
                pixel_value = radar_img.getpixel((x, y))
                result_value = result_img.getpixel((x, y))

                # first draw all white pixel that includes the target pixels
                if img_num == 1:
                    if is_color_equal(pixel_value, (255, 255, 255), 5):
                        result_draw.point((x, y), (255, 255, 255))
                # then remove echo pixels in each iteration after the first one
                else:
                    if is_color_equal(result_value, (255, 255, 255), 5):
                        if not is_color_equal(pixel_value, (255, 255, 255), 5):
                            result_draw.point((x, y), (0, 0, 0))

    # Check result folder path
    if not os.path.exists(result_folder):
        os.makedirs(result_folder)

    # Save result
    extract_result_path = result_folder + "white_boundary_" + str(station_num) + ".png"
    result_img.save(extract_result_path)
    return extract_result_path


if __name__ == "__main__":
    images_folder_path = ""
    radar_station_num = "Z9756"
    extract_result_folder_path = ""
    extract_white_boundary(images_folder_path, radar_station_num, extract_result_folder_path)
