import os
from os.path import join

from pythonforandroid.recipe import Recipe
from pythonforandroid.toolchain import shprint, current_directory

import sh


class PiperRecipe(Recipe):

    version = "1.4.2"

    url = (
        "https://github.com/OHF-Voice/"
        "piper1-gpl/archive/refs/tags/"
        "v{version}.tar.gz"
    )

    depends = [
        "python3"
    ]

    call_hostpython_via_targetpython = False

    def get_recipe_env(self, arch):

        env = super().get_recipe_env(arch)

        env["CC"] = self.ctx.cc
        env["CXX"] = self.ctx.cxx
        env["AR"] = self.ctx.ar
        env["RANLIB"] = self.ctx.ranlib

        return env

    def build_arch(self, arch):

        build_dir = self.get_build_dir(
            arch.arch
        )

        install_dir = join(
            build_dir,
            "android-install"
        )

        cmake_dir = join(
            build_dir,
            "cmake-build"
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
                "ANDROID_NDK_HOME was not found."
            )

        abi = arch.arch

        if abi == "arm64-v8a":
            android_abi = "arm64-v8a"

        elif abi == "armeabi-v7a":
            android_abi = "armeabi-v7a"

        elif abi == "x86":
            android_abi = "x86"

        elif abi == "x86_64":
            android_abi = "x86_64"

        else:

            raise RuntimeError(
                "Unsupported ABI: " +
                str(abi)
            )

        android_api = str(
            self.ctx.ndk_api
        )

        os.makedirs(
            cmake_dir,
            exist_ok=True
        )

        os.makedirs(
            install_dir,
            exist_ok=True
        )

        with current_directory(
            build_dir
        ):

            shprint(
                sh.cmake,
                "-S",
                ".",
                "-B",
                cmake_dir,

                "-G",
                "Ninja",

                "-DCMAKE_BUILD_TYPE=Release",

                "-DCMAKE_SYSTEM_NAME=Android",

                "-DCMAKE_SYSTEM_VERSION="
                + android_api,

                "-DCMAKE_ANDROID_NDK="
                + ndk,

                "-DCMAKE_ANDROID_ARCH_ABI="
                + android_abi,

                "-DCMAKE_ANDROID_STL_TYPE="
                "c++_shared",

                "-DCMAKE_INSTALL_PREFIX="
                + install_dir,

                "-DPIPER_BUILD_TESTS=OFF",

                "-DPIPER_BUILD_CLI=OFF",

                "-DPIPER_BUILD_PYTHON=OFF",

                "-DPIPER_BUILD_SHARED=ON"
            )

            shprint(
                sh.cmake,
                "--build",
                cmake_dir,
                "--config",
                "Release",
                "-j",
                str(
                    os.cpu_count() or 2
                )
            )

            shprint(
                sh.cmake,
                "--install",
                cmake_dir
            )

        lib_dir = join(
            install_dir,
            "lib"
        )

        include_dir = join(
            install_dir,
            "include"
        )

        data_dir = join(
            install_dir,
            "espeak-ng-data"
        )

        target_lib = join(
            self.ctx.get_libs_dir(
                arch.arch
            ),
            "libpiper.so"
        )

        source_lib = None

        candidates = [
            join(
                lib_dir,
                "libpiper.so"
            ),
            join(
                install_dir,
                "libpiper.so"
            )
        ]

        for candidate in candidates:

            if os.path.exists(candidate):

                source_lib = candidate
                break

        if source_lib is None:

            raise RuntimeError(
                "libpiper.so was not produced.\n"
                "Searched:\n" +
                "\n".join(candidates)
            )

        os.makedirs(
            os.path.dirname(target_lib),
            exist_ok=True
        )

        shutil_copy(
            source_lib,
            target_lib
        )

        target_data = join(
            self.ctx.get_libs_dir(
                arch.arch
            ),
            "piper-data"
        )

        if os.path.isdir(data_dir):

            shutil_copytree(
                data_dir,
                target_data
            )


def shutil_copy(source, destination):

    import shutil

    shutil.copy2(
        source,
        destination
    )


def shutil_copytree(source, destination):

    import shutil

    if os.path.exists(destination):

        shutil.rmtree(
            destination
        )

    shutil.copytree(
        source,
        destination
    )


recipe = PiperRecipe()
