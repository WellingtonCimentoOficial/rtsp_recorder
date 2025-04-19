import os

BASE_DIR = ""  # example /mnt/hd
TMP_DIR = os.path.join(BASE_DIR, "tmp")
SEGMENT_TIME = 60  # seconds
TIMEOUT = 30  # seconds
IDLE_TIME = TIMEOUT  # seconds
VIDEO_FORMAT = ".mp4"

camera_list = [
    # example {"name": "Cam1", "url": "rtsp://admin:admin@192.168.0.181:554/live/ch00_0"}
]
