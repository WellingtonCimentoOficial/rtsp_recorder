import os

BASE_DIR = ""  # example /mnt/hd
TMP_DIR = os.path.join(BASE_DIR, "tmp")
SEGMENT_TIME = 10  # seconds
TIMEOUT = 30  # seconds
IDLE_TIME = TIMEOUT  # seconds
VIDEO_FORMAT = ".mp4"

camera_list = [
    # example {"name": "Cam1", "url": "rtsp://admin:admin@192.168.0.181:554/live/ch00_0"}
]

SMTP_EMAIL_FROM = ""
SMTP_EMAIL_TO = ""
SMTP_HOST = ""
SMTP_PORT = 587
SMTP_INTERVAL = 1800
