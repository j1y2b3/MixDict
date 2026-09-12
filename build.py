"""MixDict build script."""

import os
from pathlib import Path
import shutil

import PyInstaller.__main__

from mixdict import config

ROOT_PATH = Path(__file__).resolve().parent
SPEC_FILE = "build.spec"
DIST_PATH = "dist"
WORK_PATH = "build"

def archive():
    dist_dir = ROOT_PATH / "dist"
    app_dir = dist_dir / config.APP_NAME
    platform = "win-x64"
    file_base = dist_dir / f"{config.APP_NAME}-{config.VERSION}-{platform}-portable"

    file_path = shutil.make_archive(str(file_base), "zip",
                                    root_dir=dist_dir, base_dir=config.APP_NAME)
    print(f"Archive created: {file_path}")

def build():
    args = [
        "--noconfirm",
        "--clean",
        f"--distpath={DIST_PATH}",
        f"--workpath={WORK_PATH}",
        SPEC_FILE,
    ]

    print(f"Building {config.APP_NAME}...\npyinstaller {' '.join(args)}\n")
    PyInstaller.__main__.run(args)
    print(f"\nBuilding finished: {ROOT_PATH / DIST_PATH / config.APP_NAME}")

def main():
    os.chdir(ROOT_PATH)
    build()
    archive()

if __name__ == "__main__":
    main()