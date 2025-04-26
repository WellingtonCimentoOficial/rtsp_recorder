import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv
import threading
import time
import os
from .logger import Log
from settings import SMTP_HOST, SMTP_PORT, SMTP_INTERVAL, SMTP_EMAIL_FROM, SMTP_EMAIL_TO

load_dotenv()


class Email:
    def __init__(
        self,
        smtp_host=SMTP_HOST,
        smtp_port=SMTP_PORT,
        smtp_interval=SMTP_INTERVAL,
        smtp_email_from=SMTP_EMAIL_FROM,
        smtp_email_to=SMTP_EMAIL_TO,
    ):
        self.smtp_host = smtp_host
        self.smtp_port = smtp_port
        self.smtp_interval = smtp_interval
        self.smtp_email_from = smtp_email_from
        self.smtp_email_to = smtp_email_to
        self.smtp_login_email = os.getenv("SMTP_LOGIN_EMAIL")
        self.smtp_login_password = os.getenv("SMTP_LOGIN_PASSWORD")

    def send(self, subject: str, body: str, category: str):
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = self.smtp_email_from
        msg["To"] = self.smtp_email_to
        msg.set_content(body)

        fail_count = 0

        log = Log()

        while fail_count < 3:
            try:
                with smtplib.SMTP(self.smtp_host, self.smtp_port) as smtp:
                    smtp.ehlo()
                    smtp.starttls()
                    smtp.login(self.smtp_login_email, self.smtp_login_password)
                    smtp.send_message(msg)

                log.write(
                    category=category, message="The e-mail was send successfully!"
                )
                break
            except:
                match fail_count + 1:
                    case 1:
                        log.write(
                            category=category,
                            message="The e-mail was not sent, another attempt will be made in 60 seconds...",
                            level="error",
                        )

                    case 2:
                        log.write(
                            category=category,
                            message="The e-mail was not sent, last attempt will be made in 60 seconds...",
                            level="error",
                        )

                    case 3:
                        log.write(
                            category=category,
                            message="Unable to send e-mail.",
                            level="error",
                        )

                fail_count += 1

            time.sleep(60)

    def send_async(self, subject: str, body: str, category: str):
        threading.Thread(
            target=self.send,
            args=(subject, body, category),
            daemon=True,
        ).start()
