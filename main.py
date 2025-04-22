import ffmpeg
import time
from datetime import datetime, timedelta
import os
import multiprocessing
import shutil
from settings import *
from utils import send_email, create_tmp_dir, Log
import threading
from custom_types import Camera


def start_ffmpeg(camera: Camera):
    filename = (
        camera["name"].replace(" ", "-").replace("_", "-")
        + "_%d-%m-%Y_%H-%M-%S"
        + VIDEO_FORMAT
    )
    output_path = f"{TMP_DIR}/{filename}"

    Log.write(category=Log.RTSP, message=f"Successfully connected to {camera['url']}")

    ffmpeg.input(
        camera["url"], rtsp_transport="tcp", timeout=str(TIMEOUT * 1000000)
    ).output(
        output_path,
        vcodec="copy",
        acodec="aac",
        audio_bitrate="128k",
        f="segment",
        segment_time=SEGMENT_TIME,
        reset_timestamps=1,
        strftime=1,
    ).global_args(
        "-loglevel", "error"
    ).run()


def send_email_async(subject: str, body: str, category: str):
    threading.Thread(
        target=send_email,
        args=(subject, body, category),
        daemon=True,
    ).start()


def storage_checker():
    done_event = threading.Event()

    while True:
        storage = shutil.disk_usage(BASE_DIR)
        total = round(storage.total / (1024**3), 2)
        used = round(storage.used / (1024**3), 2)
        free = round(storage.free / (1024**3), 2)
        percent_used = round((used / total) * 100, 2)

        if percent_used >= 90:
            text = f"Storage is at {percent_used}% usage."
            Log.write(category=Log.STORAGE, message=text, level="warning")
            send_email_async(
                subject=text,
                body=f"The storage is at {percent_used}% usage.\nTotal: {total}\nUsed: {used}\nFree {free}",
                category=Log.STORAGE,
            )
            done_event.wait()
            break

        time.sleep(5)


def record_stream(camera: Camera):
    last_email_sent = datetime.now() - timedelta(hours=1)

    while True:
        try:
            start_ffmpeg(camera)
        except ffmpeg.Error:
            Log.write(
                category=Log.RTSP,
                message=f"The connection dropped. Trying to connect again to {camera['url']} in 5 seconds...",
                level="error",
            )

        if (datetime.now() - last_email_sent).total_seconds() >= SMTP_INTERVAL:
            send_email_async(
                subject=f"{camera['name']} is down!",
                body=f"The connection to {camera['name']} is down",
                category=Log.RTSP,
            )
            last_email_sent = datetime.now()

        time.sleep(5)


def is_idle(file_path: str, idle_seconds: int):
    last_modified = os.path.getmtime(file_path)
    return (time.time() - last_modified) > idle_seconds


def replace_metadata(filepath: str, camera_name: str, filename: str, output_path: str):
    try:
        title = filename.replace(VIDEO_FORMAT, "")

        ffmpeg.input(filepath).output(
            output_path,
            c="copy",
            **{"metadata": "title=" + title},
        ).run()

        os.remove(filepath)

        Log.write(
            category=Log.METADATA, message=f"Metadata added to {camera_name} {filename}"
        )
    except ffmpeg.Error:
        Log.write(
            category=Log.METADATA,
            message=f"Error replacing metadata {camera_name} {filename}",
            level="error",
        )


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
                    camera_name=camera_name_str,
                    filename=new_filename,
                    output_path=os.path.join(camera_dir, new_filename),
                )

                Log.write(
                    category=Log.ORGANIZER,
                    message=f"{new_filename} moved to {camera_dir}",
                )
            except Exception as e:
                Log.write(
                    category=Log.ORGANIZER,
                    message=f"Error moving {filename}: {e}",
                    level="error",
                )

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

    storagechecker = multiprocessing.Process(target=storage_checker)
    storagechecker.start()

    processes.append(organizer)
    processes.append(storagechecker)

    for process in processes:
        process.join()


if __name__ == "__main__":
    run()
