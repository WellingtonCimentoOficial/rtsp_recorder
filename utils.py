import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv
import os
from settings import *
import shutil
import time
import logging
from custom_types import Level, Camera
import threading
import ffmpeg

load_dotenv()


class Log:
    STORAGE = "[STORAGE]"
    RTSP = "[RTSP]"
    ORGANIZER = "[ORGANIZER]"
    METADATA = "[METADATA]"

    _logger_initialized = False

    @classmethod
    def _initialize_logger(cls):
        if cls._logger_initialized:
            return

        log_path = os.path.join(BASE_DIR, "log.txt")

        logging.basicConfig(
            filename=log_path,
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%d-%m-%Y %H:%M:%S",
        )
        cls._logger_initialized = True

    @classmethod
    def write(
        cls,
        category: str,
        message: str,
        level: Level = "info",
    ):
        cls._initialize_logger()

        level = level.lower()

        if level == "info":
            logging.info(f"{category} {message}")
        elif level == "error":
            logging.error(f"{category} {message}")
        elif level == "warning":
            logging.warning(f"{category} {message}")
        elif level == "critical":
            logging.critical(f"{category} {message}")
        else:
            logging.info(f"{category} {message}")


def send_email(subject: str, body: str, category: str):
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = SMTP_EMAIL_FROM
    msg["To"] = SMTP_EMAIL_TO
    msg.set_content(body)

    smtp_email = os.getenv("SMTP_LOGIN_EMAIL")
    smtp_password = os.getenv("SMTP_LOGIN_PASSWORD")

    fail_count = 0

    while fail_count < 3:
        try:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as smtp:
                smtp.ehlo()
                smtp.starttls()
                smtp.login(smtp_email, smtp_password)
                smtp.send_message(msg)

            Log.write(category=category, message="The e-mail was send successfully!")
            break
        except:
            match fail_count + 1:
                case 1:
                    Log.write(
                        category=category,
                        message="The e-mail was not sent, another attempt will be made in 60 seconds...",
                        level="error",
                    )

                case 2:
                    Log.write(
                        category=category,
                        message="The e-mail was not sent, last attempt will be made in 60 seconds...",
                        level="error",
                    )

                case 3:
                    Log.write(
                        category=category,
                        message="Unable to send e-mail.",
                        level="error",
                    )

            fail_count += 1

        time.sleep(60)


def create_tmp_dir():
    if os.path.exists(TMP_DIR):
        shutil.rmtree(TMP_DIR)

    os.makedirs(TMP_DIR, exist_ok=True)


def start_ffmpeg(camera: Camera):
    filename = (
        camera["name"].replace(" ", "-").replace("_", "-")
        + "_%d-%m-%Y_%H-%M-%S"
        + VIDEO_FORMAT
    )
    output_path = f"{TMP_DIR}/{filename}"

    Log.write(category=Log.RTSP, message=f"Trying to connect to {camera['url']}...")

    process = (
        ffmpeg.input(
            camera["url"], rtsp_transport="tcp", timeout=str(TIMEOUT * 1000000)
        )
        .output(
            output_path,
            vcodec="copy",
            acodec="aac",
            audio_bitrate="128k",
            f="segment",
            segment_time=SEGMENT_TIME,
            reset_timestamps=1,
            strftime=1,
        )
        .global_args("-loglevel", "error")
        .run_async()
    )

    time.sleep(5)

    if process.poll() is None:
        Log.write(
            category=Log.RTSP, message=f"Successfully connected to {camera['url']}"
        )
        send_email_async(
            subject=f"{camera['name']} is up!",
            body=f"Successfully connected to {camera['name']}",
            category=Log.RTSP,
        )

    return process


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
                body=f"Total: {total}\nUsed: {used}\nFree: {free}",
                category=Log.STORAGE,
            )
            done_event.wait()
            break

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
