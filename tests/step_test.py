import re
def check_station_number_format(s):
    return bool(re.fullmatch(r'Z\d{4}', s))


img_path = "C:/Users/Blavor/Desktop/中气旋数据集/2024/4.30珠海超单/Z9755/vel/Z_RADR_I_Z9755_202404301154_P_DOR_SAD_V_5_115_15.755.png.png"
img_name = img_path.split("/")[-1]
print(img_name)
station_number = img_name.split("_")[3]
print(station_number)
print(check_station_number_format(station_number))
print(check_station_number_format("Z29"))

