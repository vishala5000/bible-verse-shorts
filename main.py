import threading

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

from src.generator import generate_videos


class BibleVerseShortsApp(App):

    def build(self):
        self.title = "Bible Verse Shorts"

        root = BoxLayout(
            orientation="vertical",
            padding=dp(14),
            spacing=dp(10)
        )

        title = Label(
            text="BIBLE VERSE SHORTS",
            font_size=dp(24),
            size_hint_y=None,
            height=dp(45),
            bold=True
        )

        root.add_widget(title)

        info = Label(
            text=(
                "Enter one Bible verse per line.\n"
                "Example: Verse — Genesis 1:1"
            ),
            size_hint_y=None,
            height=dp(55),
        )

        root.add_widget(info)

        self.input_box = TextInput(
            multiline=True,
            font_size=dp(17),
            foreground_color=(0, 0, 0, 1),
            background_color=(1, 1, 1, 1),
            cursor_color=(0, 0, 0, 1),
            hint_text=(
                "Paste Bible verses here...\n\n"
                "In the beginning God created the heaven "
                "and the earth. — Genesis 1:1"
            ),
            padding=[
                dp(12),
                dp(12),
                dp(12),
                dp(12)
            ],
        )

        root.add_widget(
            self.input_box
        )

        self.generate_button = Button(
            text="GENERATE VIDEOS",
            size_hint_y=None,
            height=dp(55),
            font_size=dp(18),
            bold=True,
        )

        self.generate_button.bind(
            on_release=self.start_generation
        )

        root.add_widget(
            self.generate_button
        )

        self.progress = ProgressBar(
            max=100,
            value=0,
            size_hint_y=None,
            height=dp(12)
        )

        root.add_widget(
            self.progress
        )

        self.status = Label(
            text="Ready",
            size_hint_y=None,
            height=dp(45),
        )

        root.add_widget(
            self.status
        )

        return root

    def start_generation(self, *_):
        text = self.input_box.text.strip()

        if not text:
            self.status.text = (
                "Please enter at least one Bible verse."
            )
            return

        lines = [
            line.strip()
            for line in text.splitlines()
            if line.strip()
        ]

        self.generate_button.disabled = True
        self.progress.value = 0

        thread = threading.Thread(
            target=self.worker,
            args=(lines,),
            daemon=True
        )

        thread.start()

    def worker(self, lines):
        try:
            total = len(lines)

            Clock.schedule_once(
                lambda dt: self.set_status(
                    f"Generating {total} video(s)..."
                )
            )

            videos, zip_path = generate_videos(
                lines
            )

            Clock.schedule_once(
                lambda dt: self.finished(
                    len(videos),
                    str(zip_path)
                )
            )

        except Exception as exc:
            message = str(exc)

            Clock.schedule_once(
                lambda dt: self.failed(
                    message
                )
            )

    def set_status(self, text):
        self.status.text = text

    def finished(self, count, zip_path):
        self.progress.value = 100

        self.status.text = (
            f"Finished: {count} video(s)\n"
            f"ZIP: {zip_path}"
        )

        self.generate_button.disabled = False

    def failed(self, message):
        self.status.text = (
            "Generation failed:\n"
            + message
        )

        self.generate_button.disabled = False


if __name__ == "__main__":
    BibleVerseShortsApp().run()
