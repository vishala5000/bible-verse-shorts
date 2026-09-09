from pathlib import Path
import shutil
import tarfile
import zipfile

from pythonforandroid.recipe import Recipe
from pythonforandroid.toolchain import current_directory, shprint
import sh


class OnnxRuntimeRecipe(Recipe):
    version = "1.22.0"

    url = (
        "https://repo1.maven.org/maven2/com/microsoft/onnxruntime/"
        "onnxruntime-android/{version}/"
        "onnxruntime-android-{version}.aar"
    )

    depends = []

    def build_arch(self, arch):
        if arch.arch != "arm64-v8a":
            raise RuntimeError(
                "This application currently supports arm64-v8a only."
            )

        build_dir = Path(self.get_build_dir(arch.arch))
        aar = build_dir / f"onnxruntime-android-{self.version}.aar"
        extracted = build_dir / "aar"

        extracted.mkdir(parents=True, exist_ok=True)

        if not aar.exists():
            raise RuntimeError(
                f"ONNX Runtime AAR not found: {aar}"
            )

        with zipfile.ZipFile(aar, "r") as z:
            z.extractall(extracted)

        native_lib = (
            extracted
            / "jni"
            / "arm64-v8a"
            / "libonnxruntime.so"
        )

        if not native_lib.exists():
            raise RuntimeError(
                "ONNX Runtime ARM64 library was not found:\n"
                f"{native_lib}"
            )

        headers = extracted / "headers"

        if not headers.exists():
            raise RuntimeError(
                "ONNX Runtime headers were not found in the AAR."
            )

        target_lib_dir = Path(
            self.ctx.get_libs_dir(arch.arch)
        )

        target_lib_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        shutil.copy2(
            native_lib,
            target_lib_dir / "libonnxruntime.so"
        )

        include_dir = (
            Path(self.ctx.get_python_install_dir())
            / "include"
            / "onnxruntime"
        )

        include_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        for header in headers.glob("*.h"):
            shutil.copy2(
                header,
                include_dir / header.name
            )

        # Also expose the headers to recipes that look inside the
        # recipe build directory.
        local_include = build_dir / "include"
        local_include.mkdir(
            parents=True,
            exist_ok=True
        )

        for header in headers.glob("*.h"):
            shutil.copy2(
                header,
                local_include / header.name
            )


recipe = OnnxRuntimeRecipe()
