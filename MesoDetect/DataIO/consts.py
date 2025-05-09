"""
    This file defines constant data that are used in radar image process algorithm,
    radar image config data are not within this scope
"""
from pathlib import Path

VALID_IMG_EXTENSION = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}


SURROUNDING_OFFSETS = [(0, -1), (0, 1), (-1, 0), (1, 0), (-1, -1), (-1, 1), (1, -1), (1, 1)]


NARROW_SURROUNDING_OFFSETS = [(0, -1), (0, 1), (-1, 0), (1, 0)]


NEED_COVER_BOUNDARY_STATIONS = ["Z9755", "Z9762", "Z9763"]


GRAY_SCALE_UNIT = 17


BASEMAP_IMG_PATH = str(Path(__file__).parent.parent.parent / "data/basemaps") + "/"


CONFIG_FILE = str(Path(__file__).parent.parent.parent / "MesoDetect/DataIO/radar_config.yaml")
