# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec for the meta-mcp Tauri sidecar backend.

Entry is the dual-mode mcpb/run_server.py (frozen: MCP_PORT/PORT env wins,
else stdio). See MCPB_PACKAGING_STANDARDS.md section 2.5 and
TAURI_PRODUCTION_PITFALLS.md section E.
"""

import sys

sys.setrecursionlimit(5000)

from PyInstaller.building.build_main import Analysis, EXE, PYZ
from PyInstaller.utils.hooks import collect_all, collect_submodules

_pydantic_all = []
try:
    _pydantic_all = collect_submodules("pydantic")
except Exception:
    _pydantic_all = [
        "pydantic.networks",
        "pydantic.color",
        "pydantic.types",
        "pydantic.v1",
    ]

_cachetools_datas, _cachetools_binaries, _cachetools_hidden = collect_all("cachetools")
_keyvalue_datas, _keyvalue_binaries, _keyvalue_hidden = collect_all("key_value")

a = Analysis(
    ["mcpb/run_server.py"],
    pathex=["src", "mcpb"],
    binaries=[],
    datas=[("src/meta_mcp", "meta_mcp")],
    hiddenimports=[
        "uvicorn.logging",
        "uvicorn.loops",
        "uvicorn.loops.asyncio",
        "uvicorn.protocols",
        "uvicorn.protocols.http",
        "uvicorn.protocols.http.httptools_impl",
        "uvicorn.protocols.http.h11_impl",
        "uvicorn.lifespan",
        "uvicorn.lifespan.on",
        "cachetools",
        "joserfc",
        "joserfc.jwk",
        "joserfc.jwt",
        "mcp.types",
        "fastmcp",
        "h11",
        "beartype",
        "websockets",
        "sqlite3",
        "jwt",
        "pytz",
        "jsonschema",
        "_strptime",
        "_datetime",
    ]
    + _pydantic_all
    + _cachetools_hidden
    + _keyvalue_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "setuptools", "pip", "wheel", "test", "tests", "unittest", "_distutils_hack"],
    noarchive=True,
    optimize=0,
)

# Strip .dist-info but preserve metadata for packages that read their own
# version at runtime. Match on separator-prefixed names so 'mcp-' does not
# swallow 'fastmcp-' (different package).
_keep_dist = ["\\mcp-", "/mcp-", "\\fastmcp-", "/fastmcp-", "\\fastapi-", "/fastapi-", "\\pydantic-", "/pydantic-"]
_saved = [
    e
    for e in a.datas
    if isinstance(e, tuple) and any(k in str(e[0]) for k in _keep_dist) and ".dist-info" in str(e[0])
]
for _list in [a.datas, a.binaries, a.zipfiles, a.scripts]:
    _list[:] = [e for e in _list if not (isinstance(e, tuple) and ".dist-info" in str(e[0]))]
a.datas.extend(_saved)
a.datas.extend(_cachetools_datas)
a.binaries.extend(_cachetools_binaries)
a.datas.extend(_keyvalue_datas)
a.binaries.extend(_keyvalue_binaries)

SKIP = [
    "torch", "playwright", "bitsandbytes", "llvmlite", "pyarrow", "pymupdf",
    "grpc", "numba", "Cython", "google", "azure", "boto3", "botocore",
    "matplotlib", "PIL", "pandas", "scipy", "sklearn", "onnxruntime",
]
a.binaries = [b for b in a.binaries if not any(s in b[0].lower() for s in SKIP)]

pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name="meta-mcp-backend",
    debug=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    # console=True: with console=False sys.stderr is None and uvicorn
    # logging crashes (TAURI_PRODUCTION_PITFALLS). The Rust spawn uses
    # CREATE_NO_WINDOW, so no window flashes.
    console=True,
)
