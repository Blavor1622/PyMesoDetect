import fill_blank
import read_radar
import blur
import time

if __name__ == '__main__':
    # set resource path
    start = time.time()
    radar_img_path = 'test_imgs/fill_test.png'
    folder_path = './result/test3'

    # read radar image
    read_result_img_path = read_radar.process_rlt_saving(folder_path, radar_img_path)

    # fill_test
    filled_img_path = fill_blank.process_rlt_saving(folder_path, read_result_img_path)

    # removing blur
    blur.remove_velocity_blur(folder_path, filled_img_path)
    end = time.time()
    total_cost = end - start
    print('--------------------')
    print(f'total cost: {total_cost:.4f} seconds')
