import os
import threading
import zipfile
from pathlib import Path

from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.progressbar import ProgressBar
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput

from src.generator import VideoGenerator


class BibleVerseShortsApp(App):

    def build(self):
        self.title = "Bible Verse Shorts"

        Window.clearcolor = (0.05, 0.05, 0.05, 1)

        root = BoxLayout(
            orientation="vertical",
            padding=dp(12),
            spacing=dp(10)
        )

        title = Label(
            text="BIBLE VERSE SHORTS",
            font_size=dp(24),
            bold=True,
            size_hint_y=None,
            height=dp(50)
        )

        root.add_widget(title)

        info = Label(
            text="Enter one Bible verse per line.\n"
                 "Example: In the beginning God created the heaven and the earth. — Genesis 1:1",
            font_size=dp(14),
            size_hint_y=None,
            height=dp(60)
        )

        root.add_widget(info)

        self.input_box = TextInput(
            multiline=True,
            font_size=dp(17),
            foreground_color=(0, 0, 0, 1),
            background_color=(1, 1, 1, 1),
            cursor_color=(0, 0, 0, 1),
            padding=[dp(12), dp(12)],
            hint_text="Paste Bible verses here...",
            hint_text_color=(0.4, 0.4, 0.4, 1)
        )

        root.add_widget(self.input_box)

        self.progress = ProgressBar(
            max=100,
            value=0,
            size_hint_y=None,
            height=dp(12)
        )

        root.add_widget(self.progress)

        self.status = Label(
            text="Ready",
            font_size=dp(14),
            size_hint_y=None,
            height=dp(40)
        )

        root.add_widget(self.status)

        buttons = BoxLayout(
            size_hint_y=None,
            height=dp(55),
            spacing=dp(8)
        )

        self.generate_button = Button(
            text="GENERATE VIDEOS",
            font_size=dp(16)
        )

        self.generate_button.bind(
            on_release=self.start_generation
        )

        buttons.add_widget(self.generate_button)

        self.zip_button = Button(
            text="ZIP VIDEOS",
            font_size=dp(16)
        )

        self.zip_button.bind(
            on_release=self.create_zip
        )

        buttons.add_widget(self.zip_button)

        root.add_widget(buttons)

        return root

    def start_generation(self, *_):

        text = self.input_box.text.strip()

        if not text:
            self.status.text = "Please enter at least one verse."
            return

        lines = [
            line.strip()
            for line in text.splitlines()
            if line.strip()
        ]

        self.generate_button.disabled = True

        self.status.text = "Starting..."

        thread = threading.Thread(
            target=self.generate_worker,
            args=(lines,),
            daemon=True
        )

        thread.start()

    def generate_worker(self, lines):

        try:

            generator = VideoGenerator(
                progress_callback=self.update_progress,
                status_callback=self.update_status
            )

            generator.generate_all(lines)

            Clock.schedule_once(
                lambda dt: self.generation_finished()
            )

        except Exception as exc:

            message = str(exc)

            Clock.schedule_once(
                lambda dt: self.generation_failed(message)
            )

    def update_progress(self, current, total):

        percent = 0

        if total:
            percent = int(
                (current / total) * 100
            )

        Clock.schedule_once(
            lambda dt: setattr(
                self.progress,
                "value",
                percent
            )
        )

    def update_status(self, message):

        Clock.schedule_once(
            lambda dt: setattr(
                self.status,
                "text",
                str(message)
            )
        )

    def generation_finished(self):

        self.progress.value = 100

        self.status.text = (
            "Generation completed."
        )

        self.generate_button.disabled = False

    def generation_failed(self, message):

        self.status.text = (
            "ERROR: " + message
        )

        self.generate_button.disabled = False

    def create_zip(self, *_):

        try:

            generator = VideoGenerator()

            zip_path = generator.create_zip()

            self.status.text = (
                "ZIP created: " +
                str(zip_path)
            )

        except Exception as exc:

            self.status.text = (
                "ZIP ERROR: " +
                str(exc)
            )


if __name__ == "__main__":
    BibleVerseShortsApp().run()
