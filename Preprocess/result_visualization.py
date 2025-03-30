from PIL import Image, ImageDraw
import os
import utils


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
    radar_zone = utils.get_radar_info("radar_zone")
    gray_value_interval = utils.gray_value_interval
    cv_pairs = utils.get_color_bar_info("color_velocity_pairs")
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
