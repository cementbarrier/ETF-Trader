# -*- mode: python ; coding: utf-8 -*-
a = Analysis(
    ['gui.py'],
    pathex=[r'E:\etf-trader'],
    binaries=[],
    datas=[
        ('config/settings.json', 'config'),
        ('backend', 'backend'),
        (r'D:\Program Files\Tencent\Marvis\MarvisAgent\1.0.1100.349\runtime\python311\Lib\site-packages\akshare\file_fold', 'akshare/file_fold'),
    ],
    hiddenimports=['pandas', 'numpy', 'requests', 'urllib3', 'charset_normalizer', 'certifi', 'idna'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'scipy', 'PIL', 'tkinter.test'],
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
