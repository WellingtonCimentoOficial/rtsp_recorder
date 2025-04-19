import ffmpeg
import time
from datetime import datetime
import os
import multiprocessing
import shutil
from settings import *


def write_log_file(text):
    with open(os.path.join(BASE_DIR, "log.txt"), "a") as log:
        log.write(f"{text}\n")


def create_tmp_dir():
    if os.path.exists(TMP_DIR):
        shutil.rmtree(TMP_DIR)

    os.makedirs(TMP_DIR, exist_ok=True)


def record_stream(camera):
    while True:
        try:
            write_log_file(f"Successfully connected to {camera["url"]}")

            filename = (
                camera["name"].replace(" ", "-").replace("_", "-")
                + "_%d-%m-%Y_%H-%M-%S"
                + VIDEO_FORMAT
            )
            output_path = f"{TMP_DIR}/{filename}"

            ffmpeg.input(
                camera["url"], rtsp_transport="tcp", timeout=str(TIMEOUT * 1000000)
            ).output(
                output_path,
                vcodec="libx264",
                crf=18,
                preset="fast",
                acodec="aac",
                audio_bitrate="192k",
                f="segment",
                segment_time=SEGMENT_TIME,
                reset_timestamps=1,
                strftime=1,
            ).global_args(
                "-loglevel", "error"
            ).run()
            write_log_file("The connection dropped")
        except ffmpeg.Error as e:
            write_log_file(
                f"[{datetime.now()}] FFmpeg failed: {e.stderr.decode() if e.stderr else str(e)}"
            )
            write_log_file(
                f"trying to connect again to {camera["url"]} in 5 seconds..."
            )
            time.sleep(5)


def is_idle(file_path, idle_seconds):
    last_modified = os.path.getmtime(file_path)
    return (time.time() - last_modified) > idle_seconds


def replace_metadata(filepath, output_path):
    try:
        filename = os.path.basename(filepath)
        title = filename.split("_")[2].replace(VIDEO_FORMAT, "")

        ffmpeg.input(filepath).output(
            output_path,
            c="copy",
            **{"metadata": "title=" + title},
        ).run()

        os.remove(filepath)

        write_log_file(f"Metadata added to {filename}")
    except ffmpeg.Error:
        write_log_file(f"Error replacing metadata {filename}")


def organize_records():
    while True:
        for filename in os.listdir(TMP_DIR):
            filepath = os.path.join(TMP_DIR, filename)
            if not filename.endswith(VIDEO_FORMAT):
                continue
            if not os.path.isfile(filepath):
                continue
            if not is_idle(filepath, IDLE_TIME):
                continue

            try:
                date_str = filename.split("_")[1]
                camera_name_str = filename.split("_")[0].lower()
                date_dir = os.path.join(BASE_DIR, date_str)
                camera_dir = os.path.join(date_dir, camera_name_str)

                os.makedirs(date_dir, exist_ok=True)
                os.makedirs(camera_dir, exist_ok=True)

                new_filename = filename.split("_")[2]

                replace_metadata(
                    filepath=filepath,
                    output_path=os.path.join(camera_dir, new_filename),
                )

                write_log_file(f"{filename} moved to {camera_dir}")
            except Exception as e:
                write_log_file(f"Error moving {filename}: {e}")

        time.sleep(5)


def run():
    create_tmp_dir()

    processes = []

    for camera in camera_list:
        p = multiprocessing.Process(target=record_stream, args=(camera,))
        p.start()
        processes.append(p)

    organizer = multiprocessing.Process(target=organize_records)
    organizer.start()
    processes.append(organizer)

    for process in processes:
        process.join()


if __name__ == "__main__":
    run()
