import time
from datetime import datetime, timedelta
import multiprocessing
from utils import (
    create_tmp_dir,
    Log,
    Fmpeg,
    Email,
    organize_records,
    storage_checker,
)
from custom_types import Camera
from settings import SMTP_INTERVAL, camera_list


def record_stream(camera: Camera):
    last_email_sent = datetime.now() - timedelta(hours=1)

    fmpeg = Fmpeg()
    process = fmpeg.start(camera)

    email = Email()

    while True:
        if process.poll() is not None:
            if (datetime.now() - last_email_sent).total_seconds() >= SMTP_INTERVAL:
                email.send_async(
                    subject=f"{camera['name']} is down!",
                    body=f"The connection to {camera['name']} is down",
                    category=Log.RTSP,
                )
                last_email_sent = datetime.now()

            time.sleep(5)
            process = fmpeg.start(camera)

        time.sleep(1)


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
