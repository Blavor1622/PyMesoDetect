import time
from PIL import Image, ImageDraw
import os.path
import utils
'''
this file use to read a original doppler weather radar image
and generate images that use the dark base image
which is easy for latter process because of the blank pixel value is (0, 0, 0)
result images including full read result, positive velocity read result and negative read result
'''


def read_radar_img(radar_img_path):
    # open the radar image
    radar_img = Image.open(radar_img_path)

    # create a result image
    rlt_img = Image.new("RGB", radar_img.size, (0, 0, 0))
    draw = ImageDraw.Draw(rlt_img)

    rlt_img_positive = Image.new("RGB", radar_img.size, (0, 0, 0))
    draw_positive = ImageDraw.Draw(rlt_img_positive)

    rlt_img_negative = Image.new("RGB", radar_img.size, (0, 0, 0))
    draw_negative = ImageDraw.Draw(rlt_img_negative)

    # Get radar zone
    radar_zone = utils.get_radar_info("radar_zone")

    # Get positive and negative color scale
    neg_color_scales = utils.get_half_color_bar('neg')
    pos_color_scales = utils.get_half_color_bar('pos')

    # read echo pixel from radar image
    for x in range(radar_zone[0] - 1, radar_zone[1]):
        for y in range(radar_zone[0] - 1, radar_zone[1]):
            # acquire the echo color
            echo_color = radar_img.getpixel((x, y))

            # flat that indicates whether the echo color is matched in scale
            is_drawn = False

            # negative color scale matching
            for negative_scale_color in neg_color_scales:
                if utils.is_color_equal(echo_color, negative_scale_color, 10):
                    draw.point((x, y), negative_scale_color)
                    draw_negative.point((x, y), negative_scale_color)
                    is_drawn = True
                    break

            # positive color scale matching
            if not is_drawn:
                for positive_scale_color in pos_color_scales:
                    if utils.is_color_equal(echo_color, positive_scale_color, 10):
                        draw.point((x, y), positive_scale_color)
                        draw_positive.point((x, y), positive_scale_color)
                        break
    return rlt_img, rlt_img_negative, rlt_img_positive


def process_rlt_saving(folder_path, radar_img_path):
    print(f'[0] input radar image: {radar_img_path.split('/')[-1]}')
    start = time.time()
    print('[0] start radar reading...')
    # check if the path exists
    if not os.path.exists(folder_path + '/read_radar'):
        os.makedirs(folder_path + '/read_radar')

    # process the radar image
    rlt_img, rlt_img_neg, rlt_img_pos = read_radar_img(radar_img_path)

    # save images
    read_result_image_path = folder_path + '/read_radar/read_result.png'
    rlt_img.save(read_result_image_path)
    rlt_img_neg.save(folder_path + '/read_radar/neg_read_result.png')
    rlt_img_pos.save(folder_path + '/read_radar/pos_read_result.png')

    print('[0] radar reading complete!')
    end = time.time()
    duration = end - start
    print(f'[0] duration of radar reading: {duration:.4f} seconds')

    return read_result_image_path
