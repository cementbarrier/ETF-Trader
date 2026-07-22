# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules
import akshare
import os

backend_hidden = collect_submodules('backend')

# 动态定位 akshare 数据目录
akshare_data = os.path.join(os.path.dirname(akshare.__file__), 'file_fold')

a = Analysis(
    ['gui.py'],
    pathex=['.'],
    binaries=[],
    datas=[(akshare_data, 'akshare/file_fold')],
    hiddenimports=backend_hidden + [
        'pystray',
        'pystray._win32',
        'pystray._base',
        'pystray._util',
        'pystray._util.win32',
        'six',
        'six.moves.queue',
        'PIL.Image',
        'PIL.ImageDraw',
        'baostock',
        'akshare',
        'pandas',
        'easytrader',
        'pywinauto',
        'requests',
        'json',
        'datetime',
        'subprocess',
        'threading',
        'tkinter',
        'sys',
        'os',
        'pathlib',
        'typing',
        'traceback',
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
    name='gui',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
