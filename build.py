"""MixDict build script."""

import os
from pathlib import Path

import PyInstaller.__main__

from mixdict import config

ROOT_PATH = Path(__file__).resolve().parent
SPEC_FILE = "build.spec"
DIST_PATH = "dist"
WORK_PATH = "build"

def main():
    os.chdir(ROOT_PATH)

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

if __name__ == "__main__":
    main()