# Bible Verse Shorts

Android Bible Verse Shorts generator.

## Features

- Python + Kivy
- python-for-android
- No Android Studio
- No Buildozer
- ARM64 Android APK
- Local Piper TTS
- Ryan High voice
- One verse per line
- One MP4 per verse
- 1080x1920 vertical video
- H.264 video
- AAC audio
- Background music
- Bible Verse heading
- Bible reference
- Comment Amen CTA
- ZIP all videos

## Input

Each line should contain one verse.

Example:

In the beginning God created the heaven and the earth. — Genesis 1:1

And the earth was without form, and void. — Genesis 1:2

## Required assets

Place these in:

assets/

- bg.mp3
- font.ttf
- en_US-ryan-high.onnx.json

The large ONNX model is downloaded automatically by GitHub Actions
from the repository release named:

piper-voice

Asset:

en_US-ryan-high.onnx

## Build

Open GitHub:

Actions

Build Bible Verse Shorts APK

Run workflow.

The resulting APK is available under:

Artifacts

BibleVerseShorts-APK

## Architecture

ARM64:

arm64-v8a

## Native engine

Piper C/C++ library

ONNX Runtime

eSpeak-ng

FFmpeg

libx264
