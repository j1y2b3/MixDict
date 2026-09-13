"""MixDict build script."""

import logging
import os
from pathlib import Path
import shutil

import PyInstaller.__main__

from mixdict import config

ROOT_PATH = Path(__file__).resolve().parent
SPEC_FILE = "build.spec"
DIST_PATH = "dist"
WORK_PATH = "build"

def build():
    args = [
        "--noconfirm",
        "--clean",
        f"--distpath={DIST_PATH}",
        f"--workpath={WORK_PATH}",
        SPEC_FILE,
    ]

    print(f"Building {config.APP_NAME}...\npyinstaller {' '.join(args)}")
    PyInstaller.__main__.run(args)
    print(f"Building finished: {ROOT_PATH / DIST_PATH / config.APP_NAME}")

def archive():
    dist_dir = ROOT_PATH / DIST_PATH
    platform = "win-x64"
    file_base = dist_dir / f"{config.APP_NAME}-{config.VERSION}-{platform}-portable"

    print(f"\nCreating archive...")
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    file_path = shutil.make_archive(str(file_base), "zip",
                                    root_dir=dist_dir, base_dir=config.APP_NAME,
                                    logger=logger)
    print(f"Archive created: {file_path}")

def main():
    os.chdir(ROOT_PATH)
    build()
    archive()

if __name__ == "__main__":
    main()