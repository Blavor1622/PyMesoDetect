import math
from typing import Tuple

def get_azimuth(point: Tuple[int, int], origin: Tuple[int, int]) -> float:
    # Calculate distance from radar center
    center_distance = math.sqrt((origin[0] - point[0]) ** 2 + (origin[1] - point[1]) ** 2)
    if center_distance != 0.0:
        cos_theta = -(point[1] - origin[1]) / center_distance
    else:
        cos_theta = 1
    theta_radians = math.acos(cos_theta)
    theta_degrees = math.degrees(theta_radians)
    if point[0] - origin[0] < 0:
        theta_degrees = 360 - theta_degrees
    return theta_degrees

if __name__ == "__main__":
    radar_center = (300, 300)
    point_1 = (463, 160)
    angle_1 = get_azimuth(point_1, radar_center)
    point_2 = (362, 551)
    angle_2 = get_azimuth(point_2, radar_center)
    point_3 = (171, 523)
    angle_3 = get_azimuth(point_3, radar_center)
    point_4 = (55, 356)
    angle_4 = get_azimuth(point_4, radar_center)
    point_5 = (203, 125)
    angle_5 = get_azimuth(point_5, radar_center)
    print(f"angle_1: {angle_1}")
    print(f"angle_2: {angle_2}")
    print(f"angle_3: {angle_3}")
    print(f"angle_4: {angle_4}")
    print(f"angle_5: {angle_5}")
