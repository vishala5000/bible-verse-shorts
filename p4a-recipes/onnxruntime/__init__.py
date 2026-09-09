from pythonforandroid.recipe import Recipe
from pythonforandroid.toolchain import current_directory
from pythonforandroid.logger import info

import os
import urllib.request
import zipfile
import shutil


class OnnxRuntimeRecipe(Recipe):
    version = "1.22.0"

    url = "https://repo1.maven.org/maven2/com/microsoft/onnxruntime/onnxruntime-android/1.22.0/onnxruntime-android-1.22.0.aar"

    depends = []

    def get_recipe_env(self, arch):
        env = super().get_recipe_env(arch)

        # Tell dependent native builds where the ORT headers/library are.
        ort_root = self.get_build_dir(arch.arch)
        ort_include = os.path.join(ort_root, "include")
        ort_lib = os.path.join(ort_root, "lib")

        env["ONNXRUNTIME_INCLUDE_DIR"] = ort_include
        env["ONNXRUNTIME_LIBRARY"] = os.path.join(
            ort_lib, "libonnxruntime.so"
        )

        return env

    def build_arch(self, arch):
        build_dir = self.get_build_dir(arch.arch)

        os.makedirs(build_dir, exist_ok=True)

        aar_path = os.path.join(
            build_dir,
            "onnxruntime-android-1.22.0.aar"
        )

        include_dir = os.path.join(build_dir, "include")
        lib_dir = os.path.join(build_dir, "lib")

        os.makedirs(include_dir, exist_ok=True)
        os.makedirs(lib_dir, exist_ok=True)

        # Download AAR manually.
        if not os.path.exists(aar_path):
            info("Downloading ONNX Runtime Android AAR...")
            urllib.request.urlretrieve(self.url, aar_path)

        info("Extracting ONNX Runtime Android AAR...")

        with zipfile.ZipFile(aar_path, "r") as z:
            members = z.namelist()

            # Extract headers.
            for member in members:
                if member.startswith("headers/") and member.endswith(".h"):
                    filename = os.path.basename(member)

                    if filename:
                        destination = os.path.join(
                            include_dir,
                            filename
                        )

                        with z.open(member) as src, open(
                            destination, "wb"
                        ) as dst:
                            shutil.copyfileobj(src, dst)

            # Extract arm64-v8a library.
            lib_member = "jni/arm64-v8a/libonnxruntime.so"

            if lib_member not in members:
                raise RuntimeError(
                    "ONNX Runtime AAR does not contain "
                    "jni/arm64-v8a/libonnxruntime.so"
                )

            destination = os.path.join(
                lib_dir,
                "libonnxruntime.so"
            )

            with z.open(lib_member) as src, open(
                destination, "wb"
            ) as dst:
                shutil.copyfileobj(src, dst)

        info("ONNX Runtime extracted successfully.")

    def install_arch(self, arch):
        build_dir = self.get_build_dir(arch.arch)

        lib_file = os.path.join(
            build_dir,
            "lib",
            "libonnxruntime.so"
        )

        if not os.path.exists(lib_file):
            raise RuntimeError(
                "ONNX Runtime library was not built: "
                + lib_file
            )

        # Install native library for Android packaging.
        libs_dir = self.ctx.get_libs_dir(arch.arch)
        os.makedirs(libs_dir, exist_ok=True)

        shutil.copy2(
            lib_file,
            os.path.join(
                libs_dir,
                "libonnxruntime.so"
            )
        )

        info("Installed libonnxruntime.so")


recipe = OnnxRuntimeRecipe()
