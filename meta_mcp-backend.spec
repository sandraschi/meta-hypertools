# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_submodules, copy_metadata

datas = [("src/meta_mcp", "meta_mcp")]
for pkg in ("fastmcp", "fastapi", "uvicorn", "pydantic", "starlette", "prefab_ui", "httpx", "structlog"):
    try:
        datas += copy_metadata(pkg)
    except Exception:
        pass

hiddenimports = collect_submodules("meta_mcp")
hiddenimports += [
    "3c22db458360489351e4__mypyc",  # tomli mypyc fragment (Python 3.13+)
    "tomli",
    "tomli._parser",
    "tomli._re",
    "tomli._types",
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.asyncio",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.http.h11_impl",
    "uvicorn.protocols.http.httptools_impl",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
]

a = Analysis(
    ["run_server.py"],
    pathex=["src"],
    binaries=[],
    
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib", "numpy", "pandas"],
    noarchive=True,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    
    name="meta_mcp-backend",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
)








