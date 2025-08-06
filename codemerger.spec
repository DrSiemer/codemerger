# -*- mode: python ; coding: utf-8 -*-

import os
import sys

# --- Prepare data files list ---
data_files = [
    ('assets', 'assets'),
    ('default_filetypes.json', '.')
]

# Define the icon path based on the operating system
icon_path = 'assets/icon.icns' if sys.platform == 'darwin' else 'assets/icon.ico'

# Define the target architecture
target_architecture = 'universal2' if sys.platform == 'darwin' else None

a = Analysis(
    ['run.py'],
    pathex=[],
    binaries=[],
    datas=data_files,
    hiddenimports=[
        'pyperclip.pyobjc_clipboard',
        'PIL.ImageTk',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='CodeMerger',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=target_architecture,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_path,
)

# macOS .app bundle
if sys.platform == 'darwin':
    app = BUNDLE(
        exe,
        name='CodeMerger.app',
        icon=icon_path,
        bundle_identifier='nl.2shine.codemerger',
        info_plist={
            'NSHighResolutionCapable': 'True'
        }
    )