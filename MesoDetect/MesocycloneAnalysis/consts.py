from typing import Tuple, TypedDict

class MesocycloneInfo(TypedDict):
    storm_num: int
    logic_center: Tuple[int, int]
    radar_distance: float
    radar_angle: float
    shear_value: float
    neg_center: Tuple[int, int]
    neg_max_velocity: float
    pos_center: Tuple[int, int]
    pos_max_velocity: float

CURRENT_DEBUG_RESULT_FOLDER = "MesocycloneAnalysis"


CENTER_DIAMETER = 4
# (183 - 65) pixels/ 50 km = 2.36 pixel per kilometer
CENTER_DISTANCE_THRESHOLD = 24


# m/s, threshold for the rotation speed of meso
MESO_ROTATION_THRESHOLD = 9.5


# threshold for checking invalid echo ratio in the meso range
VALID_MESO_ECHO_RATIO_THRESHOLD = 0.89
