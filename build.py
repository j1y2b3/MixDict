"""MixDict build script."""

import logging
import os
import subprocess
import shutil
from pathlib import Path

import PyInstaller.__main__

from mixdict import config

ROOT_PATH = Path(__file__).resolve().parent
SPEC_FILE = "build.spec"
DIST_PATH = "dist"
WORK_PATH = "build"
PlATFORM = "win-x64"
INFO_STRING = f"{config.APP_NAME}-{config.VERSION}-{PlATFORM}"

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

def collect():
    print()
    files = ("LICENSE.md", )

    for file in files:
        target_file = ROOT_PATH / DIST_PATH / config.APP_NAME / file
        shutil.copy2(file, target_file)
        print(f"Copied {file} to {target_file.relative_to(ROOT_PATH)}")

def archive():
    dist_dir = ROOT_PATH / DIST_PATH
    file_base = dist_dir / f"{INFO_STRING}-portable"

    print(f"\nCreating archive...")
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    file_path = shutil.make_archive(str(file_base), "zip",
                                    root_dir=dist_dir, base_dir=config.APP_NAME,
                                    logger=logger)
    print(f"Archive created: {file_path}")

def setup():
    ISS_FILE = "build.iss"
    OUTPUT_BASE_FILE_NAME = f"{INFO_STRING}-setup"

    (ROOT_PATH / DIST_PATH / "config.iss").write_text(
        '\n'.join((
            f'#define AppName "{config.APP_NAME}"',
            f'#define AppDisplayName "{config.TITLE}"',
            f'#define AppExeName "{config.APP_NAME}.exe"',
            f'#define AppVersion "{config.VERSION}"',
            f'#define AppPlatform "{PlATFORM}"',
            f'#define OutputBaseFilename "{OUTPUT_BASE_FILE_NAME}"',
        )),
        encoding="utf-8"
    )
    print(f"\nCompiling installer...\niscc {ISS_FILE}")
    subprocess.run([r"iscc", ISS_FILE], check=True)
    print(f"Installer created: {ROOT_PATH / DIST_PATH / OUTPUT_BASE_FILE_NAME}.exe")

def main():
    os.chdir(ROOT_PATH)
    build()
    collect()
    archive()
    setup()

if __name__ == "__main__":
    main()