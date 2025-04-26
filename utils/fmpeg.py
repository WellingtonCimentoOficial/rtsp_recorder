import ffmpeg
from custom_types.types import Camera
from settings import TMP_DIR
from .logger import Log
import os
import time
from .email import Email


class Fmpeg:
    def __init__(
        self,
        rtsp_transport="tcp",
        vcodec="copy",
        acodec="aac",
        audio_bitrate="128k",
        timeout=30,
        video_format=".mp4",
        segment_time=300,
    ):
        self.rtsp_transport = rtsp_transport
        self.vcodec = vcodec
        self.acodec = acodec
        self.audio_bitrate = audio_bitrate
        self.timeout = timeout * 1000000
        self.video_format = video_format
        self.segment_time = segment_time

    def get_default(self):
        data = {
            "rtsp_transport": self.rtsp_transport,
            "vcodec": self.vcodec,
            "acodec": self.acodec,
            "audio_bitrate": self.audio_bitrate,
            "timeout": self.timeout / 1000000,
            "video_format": self.video_format,
            "segment_time": self.segment_time,
        }
        return data

    def start(self, camera: Camera):
        filename = (
            camera["name"].replace(" ", "-").replace("_", "-")
            + "_%d-%m-%Y_%H-%M-%S"
            + self.video_format
        )
        output_path = f"{TMP_DIR}/{filename}"

        email = Email()

        log = Log()

        log.write(category=log.RTSP, message=f"Trying to connect to {camera['url']}...")

        process = (
            ffmpeg.input(
                camera["url"],
                rtsp_transport=self.rtsp_transport,
                timeout=str(self.timeout),
            )
            .output(
                output_path,
                vcodec=self.vcodec,
                acodec=self.acodec,
                audio_bitrate=self.audio_bitrate,
                f="segment",
                segment_time=self.segment_time,
                reset_timestamps=1,
                strftime=1,
            )
            .global_args("-loglevel", "error")
            .run_async()
        )

        time.sleep(5)

        if process.poll() is None:
            log.write(
                category=log.RTSP, message=f"Successfully connected to {camera['url']}"
            )
            email.send_async(
                subject=f"{camera['name']} is up!",
                body=f"Successfully connected to {camera['name']}",
                category=log.RTSP,
            )

        return process

    def replace_metadata(
        self, filepath: str, camera_name: str, filename: str, output_path: str
    ):
        log = Log()

        try:
            title = filename.replace(self.video_format, "")

            ffmpeg.input(filepath).output(
                output_path,
                c="copy",
                **{"metadata": "title=" + title},
            ).run()

            os.remove(filepath)

            log.write(
                category=log.METADATA,
                message=f"Metadata added to {camera_name} {filename}",
            )
        except ffmpeg.Error:
            log.write(
                category=log.METADATA,
                message=f"Error replacing metadata {camera_name} {filename}",
                level="error",
            )
