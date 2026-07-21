# -*- mode: python ; coding: utf-8 -*-
a = Analysis(
    ['gui.py'],
    pathex=[r'E:\etf-trader'],
    binaries=[],
    datas=[
        ('config/settings.json', 'config'),
        ('backend', 'backend'),
    ],
    hiddenimports=['pandas', 'numpy', 'baostock', 'easytrader', 'pywinauto', 'win32api', 'win32com', 'win32con', 'win32gui', 'PIL', 'PIL.Image', 'PIL.ImageGrab'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'scipy', 'tkinter.test'],
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
    name='etf-trader',
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
