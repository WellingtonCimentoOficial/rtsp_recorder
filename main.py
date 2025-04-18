import ffmpeg
import time
from datetime import datetime
import os
import multiprocessing
import shutil

BASE_DIR = ""
TMP_DIR = os.path.join(BASE_DIR, "tmp")
RTSP_URL = ""  # example rtsp://username:password@ip:port/live/ch00_0
SEGMENT_TIME = 60  # seconds
TIMEOUT = 30  # seconds
IDLE_TIME = TIMEOUT  # seconds
VIDEO_FORMAT = ".mp4"


def write_log_file(text):
    with open(os.path.join(BASE_DIR, "log.txt"), "a") as log:
        log.write(f"{text}\n")


def create_tmp_dir():
    if os.path.exists(TMP_DIR):
        shutil.rmtree(TMP_DIR)
    
    os.makedirs(TMP_DIR, exist_ok=True)


def record_stream():
    while True:
        try:
            write_log_file(f"Successfully connected to {RTSP_URL}")
            (
                ffmpeg.input(
                    RTSP_URL, rtsp_transport="tcp", timeout=str(TIMEOUT * 1000000)
                )
                .output(
                    f"{TMP_DIR}/%d-%m-%Y_%H-%M-%S{VIDEO_FORMAT}",
                    c="copy",
                    f="segment",
                    segment_time=SEGMENT_TIME,
                    reset_timestamps=1,
                    strftime=1,
                    **{"c:a": "aac", "b:a": "128k"},
                )
                .global_args("-loglevel", "error")
                .run()
            )
            write_log_file("The connection dropped")
        except ffmpeg.Error as e:
            write_log_file(
                f"[{datetime.now()}] FFmpeg failed: {e.stderr.decode() if e.stderr else str(e)}"
            )
            write_log_file(f"trying to connect again to {RTSP_URL} in 5 seconds...")
            time.sleep(5)


def is_idle(file_path, idle_seconds):
    last_modified = os.path.getmtime(file_path)
    return (time.time() - last_modified) > idle_seconds


def replace_metadata(filepath, output_path):
    try:
        filename = os.path.basename(filepath)

        ffmpeg.input(filepath).output(
            output_path,
            c="copy",
            **{"metadata": "title=" + filename.replace(VIDEO_FORMAT, "")},
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
                date_str = filename.split("_")[0]
                target_dir = os.path.join(BASE_DIR, date_str)

                os.makedirs(target_dir, exist_ok=True)

                replace_metadata(filepath, os.path.join(target_dir, filename))

                write_log_file(f"{filename} moved to {target_dir}")
            except Exception as e:
                write_log_file(f"Error moving {filename}: {e}")

        time.sleep(5)


if __name__ == "__main__":
    create_tmp_dir()

    p1 = multiprocessing.Process(target=record_stream)
    p2 = multiprocessing.Process(target=organize_records)

    p1.start()
    p2.start()

    p1.join()
    p2.join()
