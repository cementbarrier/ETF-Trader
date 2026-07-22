# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['gui.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('D:/Program Files/Tencent/Marvis/MarvisAgent/1.0.1100.349/runtime/python311/Lib/site-packages/akshare/file_fold', 'akshare/file_fold'),
    ],
    hiddenimports=[
        'easytrader', 'pywinauto', 'win32api', 'baostock', 'akshare',
        'PIL', 'PIL.Image', 'PIL.ImageDraw',
        'pystray', 'pystray._win32', 'pystray._base',
        'pystray._util', 'pystray._util.win32',
        'six', 'six.moves.queue',
        'threading', 'queue',
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
