import os
import re
import shutil
import subprocess
import tempfile
import wave
import zipfile
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

ASSETS_DIR = BASE_DIR / "assets"
OUTPUT_DIR = BASE_DIR / "output"

MODEL_PATH = ASSETS_DIR / "en_US-ryan-high.onnx"
MODEL_CONFIG = ASSETS_DIR / "en_US-ryan-high.onnx.json"
FONT_PATH = ASSETS_DIR / "font.ttf"
MUSIC_PATH = ASSETS_DIR / "bg.mp3"

VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
FPS = 30

VOICE_VOLUME = 1.0
MUSIC_VOLUME = 0.20

AUDIO_CODEC = "aac"
AUDIO_BITRATE = "192k"

CTA_PAUSE = 0.5

CTA_TEXT = "Comment Amen To Receive."

HEADING_TEXT = "BIBLE VERSE"
HEADING_FONT_SIZE = 100

REFERENCE_FONT_SIZE = 50

MAX_VERSE_FONT_SIZE = 90
MIN_VERSE_FONT_SIZE = 28

CTA_MAX_FONT_SIZE = 100
CTA_MIN_FONT_SIZE = 28

TOP_MARGIN = 300
BOTTOM_MARGIN = 300
LEFT_MARGIN = 200
RIGHT_MARGIN = 200

HEADING_COLOR = "yellow"
REFERENCE_COLOR = "yellow"
VERSE_COLOR = "white"
CTA_COLOR = "yellow"

HEADING_REFERENCE_GAP = 14
REFERENCE_VERSE_GAP = 32

LINE_SPACING = 0.18


class VideoGenerator:

    def __init__(
        self,
        progress_callback=None,
        status_callback=None
    ):

        self.progress_callback = (
            progress_callback or
            (lambda current, total: None)
        )

        self.status_callback = (
            status_callback or
            (lambda message: None)
        )

        OUTPUT_DIR.mkdir(
            parents=True,
            exist_ok=True
        )

        self.check_files()

    def check_files(self):

        required = [
            MODEL_PATH,
            MODEL_CONFIG,
            FONT_PATH,
            MUSIC_PATH
        ]

        missing = [
            str(path)
            for path in required
            if not path.exists()
        ]

        if missing:

            raise FileNotFoundError(
                "Missing files:\n" +
                "\n".join(missing)
            )

        if shutil.which("ffmpeg") is None:

            raise RuntimeError(
                "FFmpeg was not found."
            )

    def parse_line(self, line):

        line = line.strip()

        reference = ""

        parts = re.split(
            r"\s+[—–-]\s+",
            line,
            maxsplit=1
        )

        if len(parts) == 2:

            verse = parts[0].strip()
            reference = parts[1].strip()

        else:

            verse = line

        return verse, reference

    def run(self, command):

        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        if result.returncode != 0:

            raise RuntimeError(
                "Command failed:\n\n" +
                " ".join(command) +
                "\n\n" +
                result.stderr[-4000:]
            )

        return result

    def piper_command(self, text, wav_path):

        command = [
            "piper",
            "--model",
            str(MODEL_PATH),
            "--config",
            str(MODEL_CONFIG),
            "--output_file",
            str(wav_path)
        ]

        process = subprocess.run(
            command,
            input=text,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        if process.returncode != 0:

            raise RuntimeError(
                "Piper TTS failed:\n" +
                process.stderr
            )

    def wav_duration(self, path):

        with wave.open(
            str(path),
            "rb"
        ) as wav:

            frames = wav.getnframes()
            rate = wav.getframerate()

            if rate == 0:
                return 0

            return frames / float(rate)

    def create_silence(
        self,
        path,
        duration,
        sample_rate=22050
    ):

        samples = int(
            duration * sample_rate
        )

        with wave.open(
            str(path),
            "wb"
        ) as wav:

            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(sample_rate)

            silence = (
                b"\x00\x00" * samples
            )

            wav.writeframes(silence)

    def create_text_image(
        self,
        verse,
        reference,
        output_png,
        cta=False
    ):

        script = f"""
from PIL import Image, ImageDraw, ImageFont

W = {VIDEO_WIDTH}
H = {VIDEO_HEIGHT}

img = Image.new(
    "RGB",
    (W, H),
    "black"
)

draw = ImageDraw.Draw(img)

font_path = r"{str(FONT_PATH)}"

def load_font(size):
    return ImageFont.truetype(
        font_path,
        size
    )

def wrap_text(text, font, max_width):

    words = text.split()

    lines = []

    current = ""

    for word in words:

        test = (
            word
            if not current
            else current + " " + word
        )

        box = draw.textbbox(
            (0, 0),
            test,
            font=font
        )

        if box[2] <= max_width:
            current = test
        else:

            if current:
                lines.append(current)

            current = word

    if current:
        lines.append(current)

    return lines

def draw_centered_block(
    text,
    font,
    color,
    center_y,
    max_width,
    spacing
):

    lines = wrap_text(
        text,
        font,
        max_width
    )

    heights = []

    for line in lines:

        box = draw.textbbox(
            (0, 0),
            line,
            font=font
        )

        heights.append(
            box[3] - box[1]
        )

    total_height = sum(heights)

    total_height += int(
        max(
            0,
            len(lines) - 1
        ) *
        max(1, int(font.size * spacing))
    )

    y = center_y - total_height / 2

    for i, line in enumerate(lines):

        box = draw.textbbox(
            (0, 0),
            line,
            font=font
        )

        width = box[2] - box[0]

        x = (
            W / 2 -
            width / 2
        )

        draw.text(
            (x, y),
            line,
            fill=color,
            font=font
        )

        y += heights[i]

        if i < len(lines) - 1:
            y += int(
                font.size * spacing
            )

    return y

if {str(cta)}:

    font_size = {CTA_MAX_FONT_SIZE}

    while font_size > {CTA_MIN_FONT_SIZE}:

        font = load_font(font_size)

        lines = wrap_text(
            "{verse}",
            font,
            W - {LEFT_MARGIN} - {RIGHT_MARGIN}
        )

        if len(lines) <= 5:
            break

        font_size -= 2

    draw_centered_block(
        "{verse}",
        font,
        "{CTA_COLOR}",
        H / 2,
        W - {LEFT_MARGIN} - {RIGHT_MARGIN},
        {LINE_SPACING}
    )

else:

    heading_font = load_font(
        {HEADING_FONT_SIZE}
    )

    reference_font = load_font(
        {REFERENCE_FONT_SIZE}
    )

    verse_size = {MAX_VERSE_FONT_SIZE}

    while verse_size > {MIN_VERSE_FONT_SIZE}:

        verse_font = load_font(
            verse_size
        )

        lines = wrap_text(
            "{verse}",
            verse_font,
            W - {LEFT_MARGIN} - {RIGHT_MARGIN}
        )

        if len(lines) <= 10:
            break

        verse_size -= 2

    heading_box = draw.textbbox(
        (0, 0),
        "{HEADING_TEXT}",
        font=heading_font
    )

    heading_width = (
        heading_box[2] -
        heading_box[0]
    )

    heading_height = (
        heading_box[3] -
        heading_box[1]
    )

    heading_x = (
        W / 2 -
        heading_width / 2
    )

    heading_y = {TOP_MARGIN}

    draw.text(
        (heading_x, heading_y),
        "{HEADING_TEXT}",
        fill="{HEADING_COLOR}",
        font=heading_font
    )

    ref_y = (
        heading_y +
        heading_height +
        {HEADING_REFERENCE_GAP}
    )

    ref_box = draw.textbbox(
        (0, 0),
        "{reference}",
        font=reference_font
    )

    ref_width = (
        ref_box[2] -
        ref_box[0]
    )

    draw.text(
        (
            W / 2 -
            ref_width / 2,
            ref_y
        ),
        "{reference}",
        fill="{REFERENCE_COLOR}",
        font=reference_font
    )

    verse_y = (
        H / 2
    )

    draw_centered_block(
        "{verse}",
        verse_font,
        "{VERSE_COLOR}",
        verse_y,
        W - {LEFT_MARGIN} - {RIGHT_MARGIN},
        {LINE_SPACING}
    )

img.save(
    r"{str(output_png)}",
    "PNG"
)
"""

        script_file = (
            Path(tempfile.gettempdir()) /
            "bible_render.py"
        )

        script_file.write_text(
            script,
            encoding="utf-8"
        )

        self.run(
            [
                "python",
                str(script_file)
            ]
        )

    def make_video(
        self,
        verse,
        reference,
        number
    ):

        work_dir = (
            OUTPUT_DIR /
            ".temp"
        )

        work_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        verse_wav = (
            work_dir /
            f"{number}_verse.wav"
        )

        cta_wav = (
            work_dir /
            f"{number}_cta.wav"
        )

        silence_wav = (
            work_dir /
            f"{number}_silence.wav"
        )

        normal_png = (
            work_dir /
            f"{number}_normal.png"
        )

        cta_png = (
            work_dir /
            f"{number}_cta.png"
        )

        final_video = (
            OUTPUT_DIR /
            f"{number}.mp4"
        )

        self.status_callback(
            f"Generating voice {number}..."
        )

        self.piper_command(
            verse,
            verse_wav
        )

        self.piper_command(
            CTA_TEXT,
            cta_wav
        )

        self.create_silence(
            silence_wav,
            CTA_PAUSE
        )

        self.create_text_image(
            verse,
            reference,
            normal_png,
            cta=False
        )

        self.create_text_image(
            CTA_TEXT,
            "",
            cta_png,
            cta=True
        )

        verse_duration = self.wav_duration(
            verse_wav
        )

        silence_duration = CTA_PAUSE

        cta_duration = self.wav_duration(
            cta_wav
        )

        total_duration = (
            verse_duration +
            silence_duration +
            cta_duration
        )

        self.status_callback(
            f"Rendering video {number}..."
        )

        filter_complex = (
            "[0:v]format=yuv420p,"
            f"fps={FPS}[base];"
            "[1:a]volume=1.0[voice1];"
            "[2:a]volume=1.0[cta];"
            "[3:a]volume=0.20,"
            "aloop=loop=-1:size=2e+09,"
            "atrim=0:"
            f"{total_duration}[music];"
            "[voice1][cta]concat=n=2:v=0:a=1"
            "[voice];"
            "[voice][music]amix=inputs=2:"
            "duration=first:"
            "dropout_transition=0"
            "[audio]"
        )

        cmd = [
            "ffmpeg",
            "-y",

            "-loop",
            "1",
            "-i",
            str(normal_png),

            "-i",
            str(verse_wav),

            "-i",
            str(cta_wav),

            "-i",
            str(MUSIC_PATH),

            "-filter_complex",
            filter_complex,

            "-map",
            "[base]",

            "-map",
            "[audio]",

            "-t",
            str(total_duration),

            "-c:v",
            "libx264",

            "-preset",
            "ultrafast",

            "-crf",
            "18",

            "-pix_fmt",
            "yuv420p",

            "-c:a",
            AUDIO_CODEC,

            "-b:a",
            AUDIO_BITRATE,

            "-shortest",

            str(final_video)
        ]

        self.run(cmd)

        if not final_video.exists():

            raise RuntimeError(
                "FFmpeg did not create " +
                str(final_video)
            )

        return final_video

    def generate_all(self, lines):

        total = len(lines)

        if total == 0:
            return

        for index, line in enumerate(
            lines,
            start=1
        ):

            verse, reference = (
                self.parse_line(line)
            )

            self.make_video(
                verse,
                reference,
                index
            )

            self.progress_callback(
                index,
                total
            )

        self.status_callback(
            "All videos generated."
        )

    def create_zip(self):

        videos = sorted(
            OUTPUT_DIR.glob("*.mp4"),
            key=lambda p: int(
                p.stem
            )
            if p.stem.isdigit()
            else 999999
        )

        if not videos:

            raise RuntimeError(
                "No videos found."
            )

        zip_path = (
            OUTPUT_DIR /
            "videos.zip"
        )

        if zip_path.exists():
            zip_path.unlink()

        with zipfile.ZipFile(
            zip_path,
            "w",
            zipfile.ZIP_DEFLATED
        ) as archive:

            for video in videos:

                archive.write(
                    video,
                    video.name
                )

        return zip_path
