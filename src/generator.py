import ctypes
import os
import shutil
import subprocess
import zipfile
from pathlib import Path


APP_DIR = Path(__file__).resolve().parent.parent

ASSETS_DIR = APP_DIR / "assets"
OUTPUT_DIR = APP_DIR / "output"

MODEL_PATH = ASSETS_DIR / "en_US-ryan-high.onnx"
MODEL_CONFIG = ASSETS_DIR / "en_US-ryan-high.onnx.json"
FONT_PATH = ASSETS_DIR / "font.ttf"
MUSIC_PATH = ASSETS_DIR / "bg.mp3"

PIPER_DATA = (
    Path(os.environ.get("HOME", "/data/data"))
    / "share"
    / "espeak-ng-data"
)

if not PIPER_DATA.exists():
    candidates = [
        Path("/data/data/com.bibleverseshorts.app/files/share/espeak-ng-data"),
        APP_DIR / "share" / "espeak-ng-data",
    ]

    for candidate in candidates:
        if candidate.exists():
            PIPER_DATA = candidate
            break


def find_library(name):
    possible = [
        Path("/data/app"),
        Path("/data/data"),
        Path("/system/lib64"),
        Path("/system/lib"),
    ]

    for root in possible:
        try:
            matches = list(root.rglob(name))
            if matches:
                return matches[0]
        except Exception:
            pass

    return None


def load_piper():
    library = find_library("libpiper.so")

    if library is None:
        library = Path("libpiper.so")

    lib = ctypes.CDLL(str(library))

    lib.piper_bridge_synthesize.argtypes = [
        ctypes.c_char_p,
        ctypes.c_char_p,
        ctypes.c_char_p,
        ctypes.c_char_p,
        ctypes.c_char_p,
    ]

    lib.piper_bridge_synthesize.restype = ctypes.c_int

    return lib


def synthesize(text, wav_path):
    lib = load_piper()

    result = lib.piper_bridge_synthesize(
        str(MODEL_PATH).encode(),
        str(MODEL_CONFIG).encode(),
        str(PIPER_DATA).encode(),
        text.encode("utf-8"),
        str(wav_path).encode(),
    )

    if result != 0:
        raise RuntimeError(
            f"Piper synthesis failed with code {result}"
        )


def parse_line(line):
    line = line.strip()

    if not line:
        return None

    if "—" in line:
        verse, reference = line.rsplit(
            "—",
            1
        )
        return (
            verse.strip(),
            reference.strip()
        )

    if " - " in line:
        verse, reference = line.rsplit(
            " - ",
            1
        )
        return (
            verse.strip(),
            reference.strip()
        )

    return (
        line,
        ""
    )


def escape_drawtext(text):
    return (
        text
        .replace("\\", "\\\\")
        .replace(":", "\\:")
        .replace("'", "\\'")
        .replace(",", "\\,")
        .replace("[", "\\[")
        .replace("]", "\\]")
    )


def make_video(
    verse,
    reference,
    wav_path,
    output_path,
):
    normal_duration_cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(wav_path),
    ]

    result = subprocess.run(
        normal_duration_cmd,
        capture_output=True,
        text=True,
        check=True,
    )

    voice_duration = float(
        result.stdout.strip()
    )

    cta_wav = wav_path.with_name(
        wav_path.stem + "_cta.wav"
    )

    synthesize(
        "Comment Amen To Receive.",
        cta_wav
    )

    result = subprocess.run(
        normal_duration_cmd[:-1] + [str(cta_wav)],
        capture_output=True,
        text=True,
        check=True,
    )

    cta_duration = float(
        result.stdout.strip()
    )

    total_normal =
        voice_duration + 0.5

    width = 1080
    height = 1920

    verse_text = escape_drawtext(
        verse
    )

    reference_text = escape_drawtext(
        reference
    )

    heading = escape_drawtext(
        "BIBLE VERSE"
    )

    cta = escape_drawtext(
        "Comment Amen To Receive"
    )

    filter_complex = (
        "[0:v]"
        "scale=1080:1920,"
        "format=yuv420p,"
        f"drawtext=fontfile='{FONT_PATH}':"
        f"text='{heading}':"
        "fontcolor=yellow:"
        "fontsize=100:"
        "borderw=5:"
        "bordercolor=black:"
        "x=(w-text_w)/2:"
        "y=330,"
        f"drawtext=fontfile='{FONT_PATH}':"
        f"text='{reference_text}':"
        "fontcolor=yellow:"
        "fontsize=50:"
        "borderw=4:"
        "bordercolor=black:"
        "x=(w-text_w)/2:"
        "y=450,"
        f"drawtext=fontfile='{FONT_PATH}':"
        f"text='{verse_text}':"
        "fontcolor=white:"
        "borderw=6:"
        "bordercolor=black:"
        "fontsize=70:"
        "line_spacing=14:"
        "x=(w-text_w)/2:"
        "y=(h-text_h)/2,"
        f"trim=duration={total_normal},"
        "setpts=PTS-STARTPTS"
        "[v1];"

        "color=c=black:"
        "s=1080x1920:"
        f"d={cta_duration}:"
        "r=30,"
        f"drawtext=fontfile='{FONT_PATH}':"
        f"text='{cta}':"
        "fontcolor=yellow:"
        "borderw=5:"
        "bordercolor=black:"
        "fontsize=80:"
        "x=(w-text_w)/2:"
        "y=(h-text_h)/2,"
        "setpts=PTS-STARTPTS"
        "[v2];"

        "[v1][v2]"
        "concat=n=2:v=1:a=0,"
        "format=yuv420p"
        "[video];"

        f"anullsrc=r=22050:cl=mono,"
        f"atrim=duration={total_normal},"
        "asetpts=PTS-STARTPTS"
        "[silence];"

        "[0:a]"
        "volume=1.0,"
        "asetpts=PTS-STARTPTS"
        "[voice];"

        f"[1:a]"
        "volume=1.0,"
        "asetpts=PTS-STARTPTS"
        "[cta_voice];"

        "[voice][silence]"
        "concat=n=2:v=0:a=1"
        "[main_audio];"

        "[main_audio][cta_voice]"
        "concat=n=2:v=0:a=1"
        "[voice_final];"

        "[2:a]"
        "volume=0.20,"
        "aloop=loop=-1:size=2e+09,"
        f"atrim=duration={total_normal + cta_duration},"
        "asetpts=PTS-STARTPTS"
        "[music];"

        "[voice_final][music]"
        "amix=inputs=2:"
        "duration=longest:"
        "dropout_transition=0,"
        "aresample=async=1"
        "[audio]"
    )

    command = [
        "ffmpeg",
        "-y",

        "-f",
        "lavfi",
        "-i",
        "color=c=black:s=1080x1920:r=30",

        "-i",
        str(wav_path),

        "-i",
        str(cta_wav),

        "-stream_loop",
        "-1",
        "-i",
        str(MUSIC_PATH),

        "-filter_complex",
        filter_complex,

        "-map",
        "[video]",

        "-map",
        "[audio]",

        "-c:v",
        "libx264",

        "-preset",
        "ultrafast",

        "-crf",
        "18",

        "-pix_fmt",
        "yuv420p",

        "-r",
        "30",

        "-c:a",
        "aac",

        "-b:a",
        "192k",

        "-movflags",
        "+faststart",

        str(output_path),
    ]

    subprocess.run(
        command,
        check=True,
    )

    try:
        cta_wav.unlink()
    except Exception:
        pass


def generate_videos(lines):
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    generated = []

    for index, line in enumerate(
        lines,
        start=1
    ):
        parsed = parse_line(line)

        if not parsed:
            continue

        verse, reference = parsed

        wav_path = (
            OUTPUT_DIR
            / f"{index}.wav"
        )

        output_path = (
            OUTPUT_DIR
            / f"{index}.mp4"
        )

        synthesize(
            verse,
            wav_path
        )

        make_video(
            verse,
            reference,
            wav_path,
            output_path
        )

        try:
            wav_path.unlink()
        except Exception:
            pass

        generated.append(
            output_path
        )

    zip_path = (
        APP_DIR / "videos.zip"
    )

    with zipfile.ZipFile(
        zip_path,
        "w",
        zipfile.ZIP_DEFLATED
    ) as archive:

        for video in generated:
            archive.write(
                video,
                video.name
            )

    return generated, zip_path
