import os
import shutil
import subprocess
import urllib.request
import zipfile
from pathlib import Path

from pythonforandroid.recipe import Recipe


class PiperRecipe(Recipe):
    version = "1.4.2"

    url = (
        "https://github.com/OHF-Voice/piper1-gpl/"
        "archive/refs/tags/v{version}.tar.gz"
    )

    depends = [
        "onnxruntime",
    ]

    call_hostpython_via_targetpython = False

    def _run(self, command, cwd=None, env=None):
        print("RUN:", " ".join(str(x) for x in command))

        subprocess.run(
            [str(x) for x in command],
            cwd=str(cwd) if cwd else None,
            env=env,
            check=True,
        )

    def build_arch(self, arch):
        if arch.arch != "arm64-v8a":
            raise RuntimeError(
                "Piper recipe currently supports arm64-v8a only."
            )

        build_dir = Path(
            self.get_build_dir(arch.arch)
        )

        source_dir = build_dir

        # The Piper source archive normally extracts into:
        # piper1-gpl-1.4.2
        candidates = [
            build_dir,
            build_dir / f"piper1-gpl-{self.version}",
        ]

        for candidate in candidates:
            if (
                candidate.exists()
                and (candidate / "libpiper").exists()
            ):
                source_dir = candidate
                break

        libpiper = source_dir / "libpiper"

        if not libpiper.exists():
            raise RuntimeError(
                "Piper libpiper directory was not found:\n"
                f"{source_dir}"
            )

        ndk = os.environ.get(
            "ANDROID_NDK_HOME",
            os.environ.get(
                "ANDROID_NDK_ROOT",
                ""
            )
        )

        if not ndk:
            raise RuntimeError(
                "ANDROID_NDK_HOME / ANDROID_NDK_ROOT is missing."
            )

        api = str(
            getattr(
                self.ctx,
                "ndk_api",
                24
            )
        )

        ort_recipe_dir = Path(
            self.ctx.get_recipe_dir(
                "onnxruntime"
            )
        )

        ort_build = Path(
            self.get_recipe_build_dir(
                "onnxruntime",
                arch.arch
            )
        )

        ort_aar = (
            ort_build
            / f"onnxruntime-android-{onnx_version()}.aar"
        )

        # Locate ORT library/header data created by the
        # ONNX Runtime recipe.
        possible_ort_libs = [
            Path(self.ctx.get_libs_dir(arch.arch))
            / "libonnxruntime.so",
            ort_build
            / "aar"
            / "jni"
            / "arm64-v8a"
            / "libonnxruntime.so",
        ]

        ort_lib = None

        for candidate in possible_ort_libs:
            if candidate.exists():
                ort_lib = candidate
                break

        if ort_lib is None:
            raise RuntimeError(
                "Could not locate Android ONNX Runtime library."
            )

        possible_headers = [
            ort_build / "include",
            ort_build / "aar" / "headers",
            Path(
                self.ctx.get_python_install_dir()
            ) / "include" / "onnxruntime",
        ]

        ort_include = None

        for candidate in possible_headers:
            if (
                candidate.exists()
                and (
                    candidate / "onnxruntime_cxx_api.h"
                ).exists()
            ):
                ort_include = candidate
                break

        if ort_include is None:
            raise RuntimeError(
                "Could not locate ONNX Runtime headers."
            )

        cmake_file = source_dir / "AndroidPiperCMakeLists.txt"

        cmake_file.write_text(
            r'''
cmake_minimum_required(VERSION 3.26)

project(android_piper LANGUAGES C CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

set(PIPER_ROOT "${CMAKE_CURRENT_LIST_DIR}")

set(PIPER_SRC
    "${PIPER_ROOT}/libpiper/src/piper.cpp"
    "${PIPER_ROOT}/libpiper/src/chinese_phonemizer.cpp"
)

add_library(piper SHARED ${PIPER_SRC})

target_include_directories(
    piper
    PRIVATE
    "${PIPER_ROOT}/libpiper/include"
    "${ORT_INCLUDE}"
    "${ESPEAK_INCLUDE}"
)

add_library(
    onnxruntime
    SHARED
    IMPORTED
)

set_target_properties(
    onnxruntime
    PROPERTIES
    IMPORTED_LOCATION "${ORT_LIBRARY}"
    INTERFACE_INCLUDE_DIRECTORIES "${ORT_INCLUDE}"
)

add_library(
    espeak-ng
    STATIC
    IMPORTED
)

set_target_properties(
    espeak-ng
    PROPERTIES
    IMPORTED_LOCATION "${ESPEAK_LIBRARY}"
    INTERFACE_INCLUDE_DIRECTORIES "${ESPEAK_INCLUDE}"
)

target_link_libraries(
    piper
    PRIVATE
    espeak-ng
    onnxruntime
    log
    android
)

target_compile_definitions(
    piper
    PRIVATE
    BUILDING_LIBPIPER
    PIPER_VERSION="1.4.2"
)

set_target_properties(
    piper
    PROPERTIES
    OUTPUT_NAME "piper"
)

install(
    TARGETS piper
    LIBRARY
    DESTINATION lib
)

install(
    DIRECTORY
    "${PIPER_ROOT}/libpiper/include/"
    DESTINATION include
)

install(
    DIRECTORY
    "${ESPEAK_DATA_DIR}/"
    DESTINATION share/espeak-ng-data
)
''',
            encoding="utf-8"
        )

        # ---------------------------------------------------------
        # Build eSpeak-ng separately.
        # ---------------------------------------------------------

        espeak_root = build_dir / "espeak-ng"

        if not espeak_root.exists():
            espeak_root.mkdir(
                parents=True,
                exist_ok=True
            )

            espeak_archive = (
                build_dir
                / "espeak-ng.tar.gz"
            )

            espeak_url = (
                "https://github.com/espeak-ng/espeak-ng/"
                "archive/"
                "212928b394a96e8fd2096616bfd54e17845c48f6.tar.gz"
            )

            print(
                "Downloading eSpeak-ng..."
            )

            urllib.request.urlretrieve(
                espeak_url,
                espeak_archive
            )

            import tarfile

            with tarfile.open(
                espeak_archive,
                "r:gz"
            ) as tar:
                tar.extractall(
                    build_dir
                )

            extracted = [
                p for p in build_dir.iterdir()
                if p.is_dir()
                and p.name.startswith(
                    "espeak-ng-"
                )
            ]

            if not extracted:
                raise RuntimeError(
                    "Could not find extracted eSpeak-ng source."
                )

            shutil.move(
                str(extracted[0]),
                str(espeak_root)
            )

        espeak_build = (
            build_dir / "espeak-build"
        )

        espeak_install = (
            build_dir / "espeak-install"
        )

        espeak_build.mkdir(
            parents=True,
            exist_ok=True
        )

        espeak_install.mkdir(
            parents=True,
            exist_ok=True
        )

        toolchain = (
            Path(ndk)
            / "build"
            / "cmake"
            / "android.toolchain.cmake"
        )

        if not toolchain.exists():
            raise RuntimeError(
                "Android CMake toolchain not found:\n"
                f"{toolchain}"
            )

        espeak_cmake_args = [
            "cmake",
            "-S",
            str(espeak_root),
            "-B",
            str(espeak_build),
            "-G",
            "Ninja",
            f"-DCMAKE_TOOLCHAIN_FILE={toolchain}",
            f"-DANDROID_ABI=arm64-v8a",
            f"-DANDROID_PLATFORM=android-{api}",
            "-DCMAKE_BUILD_TYPE=Release",
            f"-DCMAKE_INSTALL_PREFIX={espeak_install}",
            "-DBUILD_SHARED_LIBS=OFF",
            "-DUSE_ASYNC=OFF",
            "-DUSE_MBROLA=OFF",
            "-DUSE_LIBSONIC=OFF",
            "-DUSE_LIBPCAUDIO=OFF",
            "-DUSE_KLATT=OFF",
            "-DUSE_SPEECHPLAYER=OFF",
            "-DEXTRA_cmn=ON",
            "-DEXTRA_ru=ON",
        ]

        self._run(
            espeak_cmake_args
        )

        self._run(
            [
                "cmake",
                "--build",
                str(espeak_build),
                "--parallel",
                str(
                    max(
                        2,
                        os.cpu_count() or 2
                    )
                ),
            ]
        )

        self._run(
            [
                "cmake",
                "--install",
                str(espeak_build),
            ]
        )

        espeak_library_candidates = [
            espeak_install
            / "lib"
            / "libespeak-ng.a",
            espeak_build
            / "src"
            / "libespeak-ng"
            / "libespeak-ng.a",
        ]

        espeak_library = None

        for candidate in (
            espeak_library_candidates
        ):
            if candidate.exists():
                espeak_library = candidate
                break

        if espeak_library is None:
            raise RuntimeError(
                "eSpeak-ng static library was not produced."
            )

        espeak_include = (
            espeak_install
            / "include"
        )

        espeak_data = (
            espeak_install
            / "share"
            / "espeak-ng-data"
        )

        if not espeak_include.exists():
            raise RuntimeError(
                "eSpeak-ng include directory was not installed."
            )

        if not espeak_data.exists():
            raise RuntimeError(
                "eSpeak-ng data directory was not installed."
            )

        # ---------------------------------------------------------
        # Build libpiper.
        # ---------------------------------------------------------

        piper_build = (
            build_dir / "piper-build"
        )

        piper_install = (
            build_dir / "piper-install"
        )

        piper_build.mkdir(
            parents=True,
            exist_ok=True
        )

        piper_install.mkdir(
            parents=True,
            exist_ok=True
        )

        piper_cmake_args = [
            "cmake",
            "-S",
            str(source_dir),
            "-B",
            str(piper_build),
            "-G",
            "Ninja",
            f"-DCMAKE_TOOLCHAIN_FILE={toolchain}",
            "-DANDROID_ABI=arm64-v8a",
            f"-DANDROID_PLATFORM=android-{api}",
            "-DCMAKE_BUILD_TYPE=Release",
            f"-DCMAKE_INSTALL_PREFIX={piper_install}",
            f"-DORT_LIBRARY={ort_lib}",
            f"-DORT_INCLUDE={ort_include}",
            f"-DESPEAK_LIBRARY={espeak_library}",
            f"-DESPEAK_INCLUDE={espeak_include}",
            f"-DESPEAK_DATA_DIR={espeak_data}",
        ]

        self._run(
            piper_cmake_args
        )

        self._run(
            [
                "cmake",
                "--build",
                str(piper_build),
                "--parallel",
                str(
                    max(
                        2,
                        os.cpu_count() or 2
                    )
                ),
            ]
        )

        self._run(
            [
                "cmake",
                "--install",
                str(piper_build),
            ]
        )

        piper_library_candidates = [
            piper_install
            / "lib"
            / "libpiper.so",
            piper_build
            / "libpiper.so",
        ]

        piper_library = None

        for candidate in (
            piper_library_candidates
        ):
            if candidate.exists():
                piper_library = candidate
                break

        if piper_library is None:
            raise RuntimeError(
                "libpiper.so was not produced."
            )

        target_lib_dir = Path(
            self.ctx.get_libs_dir(
                arch.arch
            )
        )

        target_lib_dir.mkdir(
            parents=True,
            exist_ok=True
        )

        shutil.copy2(
            piper_library,
            target_lib_dir / "libpiper.so"
        )

        # Copy Piper's native headers.
        target_include = (
            build_dir / "installed-headers"
        )

        target_include.mkdir(
            parents=True,
            exist_ok=True
        )

        for header in (
            libpiper / "include"
        ).glob("*"):
            if header.is_file():
                shutil.copy2(
                    header,
                    target_include / header.name
                )

        # Copy eSpeak data into the p4a private assets.
        data_target = (
            Path(self.ctx.get_python_install_dir())
            / "share"
            / "espeak-ng-data"
        )

        if data_target.exists():
            shutil.rmtree(
                data_target
            )

        shutil.copytree(
            espeak_data,
            data_target
        )


def onnx_version():
    return "1.22.0"


recipe = PiperRecipe()
