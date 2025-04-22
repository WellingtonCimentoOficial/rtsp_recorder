import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv
import os
from settings import (
    SMTP_EMAIL_FROM,
    SMTP_HOST,
    SMTP_PORT,
    SMTP_EMAIL_TO,
    BASE_DIR,
    TMP_DIR,
)
import shutil
from time import sleep
import logging
from custom_types import Level

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

        sleep(60)


def create_tmp_dir():
    if os.path.exists(TMP_DIR):
        shutil.rmtree(TMP_DIR)

    os.makedirs(TMP_DIR, exist_ok=True)
