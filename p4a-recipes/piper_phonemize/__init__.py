from pythonforandroid.recipe import Recipe


class PiperPhonemizeRecipe(Recipe):
    version = "1.0.0"

    depends = []

    def build_arch(self, arch):
        # Piper 1.4.x performs phonemization through its embedded
        # eSpeak-ng implementation. No separate Python package is
        # required for the Android build.
        return


recipe = PiperPhonemizeRecipe()
