import smtplib
from email.message import EmailMessage
from dotenv import load_dotenv
import os
from settings import SMTP_EMAIL_FROM, SMTP_HOST, SMTP_PORT, SMTP_EMAIL_TO

load_dotenv()


def send_email(subject, body):
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = SMTP_EMAIL_FROM
    msg["To"] = SMTP_EMAIL_TO
    msg.set_content(body)

    smtp_email = os.getenv("SMTP_LOGIN_EMAIL")
    smtp_password = os.getenv("SMTP_LOGIN_PASSWORD")

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as smtp:
        smtp.ehlo()
        smtp.starttls()
        smtp.login(smtp_email, smtp_password)
        smtp.send_message(msg)


if __name__ == "__main__":
    try:
        send_email("test", "testing...")
        print("This e-mail was send successfully!")
    except Exception as e:
        print(e)
