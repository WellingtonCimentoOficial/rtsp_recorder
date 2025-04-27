import os
import time
from .fmpeg import Fmpeg
from .logger import Log
from settings import TMP_DIR, BASE_DIR
from datetime import datetime


def create_tmp_dir():
    os.makedirs(TMP_DIR, exist_ok=True)


def is_idle(file_path: str, idle_seconds: float):
    last_modified = os.path.getmtime(file_path)
    return (time.time() - last_modified) > idle_seconds


def organize_records():
    fmpeg = Fmpeg()
    fmpeg_default = fmpeg.get_default()

    idle_time = fmpeg_default["timeout"]
    video_format = fmpeg_default["video_format"]

    log = Log()

    while True:
        for filename in os.listdir(TMP_DIR):
            filepath = os.path.join(TMP_DIR, filename)
            if not filename.endswith(video_format):
                continue
            if not os.path.isfile(filepath):
                continue
            if not is_idle(filepath, idle_time):
                continue

            try:
                date = datetime.strptime(filename.split("_")[1], "%d-%m-%Y")
                year_str = str(date.year)
                month_str = date.strftime("%B")
                day_str = str(date.day)
                camera_name_str = filename.split("_")[0].lower()
                camera_dir = os.path.join(
                    BASE_DIR, year_str, month_str, day_str, camera_name_str
                )

                os.makedirs(camera_dir, exist_ok=True)

                new_filename = filename.split("_")[2]

                fmpeg.replace_metadata(
                    filepath=filepath,
                    camera_name=camera_name_str,
                    filename=new_filename,
                    output_path=os.path.join(camera_dir, new_filename),
                )

                log.write(
                    category=log.ORGANIZER,
                    message=f"{new_filename} moved to {camera_dir}",
                )
            except Exception as e:
                log.write(
                    category=log.ORGANIZER,
                    message=f"Error moving {filename}: {e}",
                    level="error",
                )

        time.sleep(5)
