import threading
from .email import Email
from .logger import Log
from settings import BASE_DIR
import time
import shutil


def storage_checker():
    done_event = threading.Event()
    email = Email()
    log = Log()

    while True:
        storage = shutil.disk_usage(BASE_DIR)
        total = round(storage.total / (1024**3), 2)
        used = round(storage.used / (1024**3), 2)
        free = round(storage.free / (1024**3), 2)
        percent_used = round((used / total) * 100, 2)

        if percent_used >= 90:
            text = f"Storage is at {percent_used}% usage."
            log.write(category=log.STORAGE, message=text, level="warning")
            email.send_async(
                subject=text,
                body=f"Total: {total}\nUsed: {used}\nFree: {free}",
                category=log.STORAGE,
            )
            done_event.wait()
            break

        time.sleep(5)
