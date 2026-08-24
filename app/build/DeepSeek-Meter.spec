# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['../src/app.py'],
    pathex=[],
    binaries=[],
    datas=[('E:/xjzm/.qwenpaw/workspaces/uAb4YT/DeepSeekMonitor/app/app_logo.png', '.'), ('E:/xjzm/.qwenpaw/workspaces/uAb4YT/DeepSeekMonitor/app/src/app.ico', '.')],
    hiddenimports=[],
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
    name='DeepSeek-Meter',
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
    icon=['E:/xjzm/.qwenpaw/workspaces/uAb4YT/DeepSeekMonitor/app/src/app.ico'],
)
