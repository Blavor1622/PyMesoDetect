import time
from PIL import Image, ImageDraw
import os.path
from RadarPreprocess import consts
'''
this file use to read a original doppler weather radar image
and generate images that use the dark base image
which is easy for latter process because of the blank pixel value is (0, 0, 0)
result images including full read result, positive velocity read result and negative read result
'''


def read_radar_img(radar_img_path):
    # open the radar image
    radar_img = Image.open(radar_img_path)

    # draw radar image legend for base image
    v_base_img = Image.open(consts.v_base_path)
    v_base_draw = ImageDraw.Draw(v_base_img)
    for x in range(consts.legend_area[0], consts.legend_area[1]):
        for y in range(consts.legend_area[2], consts.legend_area[3]):
            legend_value = radar_img.getpixel((x, y))
            v_base_draw.point((x, y), legend_value)

    # save the updated v-base image
    v_base_img.save(consts.v_base_path)

    # create a result image
    rlt_img = Image.open(consts.v_base_path)
    draw = ImageDraw.Draw(rlt_img)

    rlt_img_positive = Image.open(consts.v_base_path)
    draw_positive = ImageDraw.Draw(rlt_img_positive)

    rlt_img_negative = Image.open(consts.v_base_path)
    draw_negative = ImageDraw.Draw(rlt_img_negative)

    # read echo pixel from radar image
    for x in range(consts.radar_area[0] - 1, consts.radar_area[1]):
        for y in range(consts.radar_area[0] - 1, consts.radar_area[1]):
            # acquire the echo color
            echo_color = radar_img.getpixel((x, y))

            # flat that indicates whether the echo color is matched in scale
            is_drawn = False

            # negative color scale matching
            for negative_scale_color in consts.negative_scale:
                if consts.is_color_equal(echo_color, negative_scale_color, 10):
                    draw.point((x, y), negative_scale_color)
                    draw_negative.point((x, y), negative_scale_color)
                    is_drawn = True
                    break

            # positive color scale matching
            if not is_drawn:
                for positive_scale_color in consts.positive_scale:
                    if consts.is_color_equal(echo_color, positive_scale_color, 10):
                        draw.point((x, y), positive_scale_color)
                        draw_positive.point((x, y), positive_scale_color)
                        is_drawn = True
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
