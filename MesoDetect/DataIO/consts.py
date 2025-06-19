"""
    This file defines constant data that are used in radar image process algorithm,
    radar image config data are not within this scope
"""
from pathlib import Path
from MesoDetect.MesocycloneAnalysis.consts import MesocycloneInfo
from typing import TypedDict, List


# List of valid image extension
VALID_IMG_EXTENSION = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}

# List of surrounding pixels coordinate offsets
SURROUNDING_OFFSETS = [(0, -1), (0, 1), (-1, 0), (1, 0), (-1, -1), (-1, 1), (1, -1), (1, 1)]

# List of surrounding pixels coordinate offsets for narrow filling
NARROW_SURROUNDING_OFFSETS = [(0, -1), (0, 1), (-1, 0), (1, 0)]

# Radar Stations that has white boundary lines which may interfere with white color echoes
NEED_COVER_BOUNDARY_STATIONS = ["Z9750", "Z9755", "Z9756", "Z9762", "Z9763"]

# Scale unit of gray color
GRAY_SCALE_UNIT = 17

# Default Image path of basemap
BASEMAP_IMG_PATH = (Path(__file__).parent.parent.parent / "data/basemaps").as_posix() + "/"

# Default radar image config file path
CONFIG_FILE = (Path(__file__).parent.parent.parent / "MesoDetect/DataIO/radar_config.yaml").as_posix()

# Default debug image folder name
CURRENT_DEBUG_RESULT_FOLDER = "DataIO/"

# Define detection result data dictionary
class DetectionResult(TypedDict):
    station_number: str
    scan_time: str
    meso_list: List[MesocycloneInfo]
    result_img_paths: List[str]
