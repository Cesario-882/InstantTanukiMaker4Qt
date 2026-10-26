# -*- mode: python ; coding: utf-8 -*-

import sys
import os
from PyInstaller.utils.hooks import collect_all

# ===== 跨平台动态依赖收集 =====
extra_binaries = []
extra_datas = []
hidden_imports = ['zstandard', 'zstandard.backend_c', 'zstandard.backend_cffi']

if sys.platform == 'win32':

    # 1. 自动收集 PySide6 的全部依赖（包含 qwindows.dll 等平台插件）
    # 这一步非常关键，防止出现 ImportError: DLL load failed
    pyside_datas, pyside_binaries, pyside_hiddenimports = collect_all('PySide6')
    extra_datas.extend(pyside_datas)
    extra_binaries.extend(pyside_binaries)
    hidden_imports.extend(pyside_hiddenimports)

    # 2. 抓取 MSVC 运行库，彻底摆脱系统依赖
    dll_names = [
        'msvcp140.dll', 'vcruntime140.dll', 'vcruntime140_1.dll',
        'concrt140.dll', 'vcomp140.dll', 'msvcp140_1.dll', 'msvcp140_2.dll'
    ]
    search_paths = []

    # 搜索当前 Python 环境目录
    if hasattr(sys, 'base_prefix'):
        search_paths.append(os.path.join(sys.base_prefix, 'DLLs'))
        search_paths.append(sys.base_prefix)

    # 搜索系统 System32 目录
    win_dir = os.environ.get('SystemRoot', r'C:\Windows')
    search_paths.append(os.path.join(win_dir, 'System32'))

    # 搜索 PySide6 目录（有时里面会自带）
    try:
        import PySide6
        search_paths.append(os.path.dirname(PySide6.__file__))
    except ImportError:
        pass

    # 遍历查找并加入到 binaries
    for name in dll_names:
        for p in search_paths:
            target = os.path.join(p, name)
            if os.path.exists(target):
                extra_binaries.append((target, '.'))
                print(f"  -> 已添加运行库: {name}")
                break

# ===== 分析配置 =====
a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=extra_binaries,
    datas=[('Data', 'Data')] + extra_datas,  # 动态合并数据
    hiddenimports=hidden_imports,            # 动态合并隐藏导入
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
    [],
    exclude_binaries=True,
    name='InstantTanukiMaker',
    debug=True,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    contents_directory='ELF_requirements',
    icon='Tanukora.ico' if sys.platform == 'win32' else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='InstantTanukiMaker',
)
