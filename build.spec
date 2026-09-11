# -*- mode: python ; coding: utf-8 -*-

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from PyInstaller.building.build_main import Analysis
    from PyInstaller.building.api import PYZ, EXE, COLLECT
    from PyInstaller.config import CONF
    SPECPATH = str()

import sys
sys.path.insert(0, SPECPATH)  # Insert the spec file directory at the front of `sys.path`.
from PyInstaller.utils.win32.versioninfo import VSVersionInfo, FixedFileInfo, StringFileInfo
from PyInstaller.utils.win32.versioninfo import StringTable, StringStruct, VarFileInfo, VarStruct
from mixdict import config

EXCLUDES = [
    'tkinter', '_tkinter', 'Tkinter',
    'unittest', 'pdb', 'doctest', 'lib2to3', 'test', 'idlelib',
    'PIL.ImageTk', 'PIL.ImageQt', 'PIL.ImageGrab', 'PIL.ImageShow', 'PIL.ImageWin',
    'pytest', '_pytest', 'pluggy', 'iniconfig', 'pygments',
    'pip', 'PyInstaller', 'cryptography',
]
VERSION_INFO = None

if sys.platform.startswith("win32"):
    ICON = 'assets/icon.ico'
    EXCLUDES += [
        'pystray._gtk', 'pystray._xorg', 'pystray._appindicator', 'pystray._darwin',
        'webview.platforms.cef', 'webview.platforms.qt',
        'webview.platforms.gtk', 'webview.platforms.cocoa', 'webview.platforms.android',
        'PyQt5', 'PyQt6', 'PySide2', 'PySide6', 'qtpy', 'gi',
    ]
    _version = config.VERSION.lstrip("v").split(".")
    _version = tuple(int(x) for x in _version) + (0,) * (4 - len(_version))
    VERSION_INFO = VSVersionInfo(
        ffi=FixedFileInfo(
            filevers=_version,
            prodvers=_version,
            mask=0x3f,
            flags=0x0,
            OS=0x40004,
            fileType=0x1,
            subtype=0x0,
            date=(0, 0),
        ),
        kids=[
            StringFileInfo([
                StringTable('080404b0', [
                    StringStruct('CompanyName', 'Jin Yubin'),
                    StringStruct('FileDescription', config.TITLE),
                    StringStruct('FileVersion', config.VERSION),
                    StringStruct('InternalName', config.APP_NAME),
                    StringStruct('LegalCopyright', 'Copyright (C) 2026 Jin Yubin. Licensed under MIT.'),
                    StringStruct('OriginalFilename', f'{config.APP_NAME}.exe'),
                    StringStruct('ProductName', config.APP_NAME),
                    StringStruct('ProductVersion', config.VERSION),
                ]),
            ]),
            VarFileInfo([VarStruct('Translation', [0x0804, 1200])]),
        ],
    )

else:
    raise SystemExit(f"MixDict does not currently support building on the {sys.platform!r} platform.")


analysis = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('assets', 'assets'),
        ('mixdict/gui/web', 'mixdict/gui/web'),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=EXCLUDES,
    noarchive=False,
    optimize=2,
)
pyz = PYZ(analysis.pure)

exe = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name=config.APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=ICON,
    version=VERSION_INFO,
)
collect = COLLECT(
    exe,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name=config.APP_NAME,
)
