"""
TRIDENT Native C++ Extension Build Script (Step 04)
Compiles matcher.cpp into a PyBind11 Python extension module: matcher_native.

Usage (from repo root):
    python backend/app/core/matcher/native/setup.py build_ext --inplace

The compiled .so (Linux/macOS) or .pyd (Windows) is placed in:
    backend/app/core/matcher/native/

engine_factory.py automatically discovers and loads the artifact when NATIVE_MATCHER=true.
"""

import os
import sys
from pathlib import Path

from setuptools import setup, Extension

# ---------------------------------------------------------------------------
# Resolve pybind11 include path — works whether pybind11 is installed as a
# package (pip install pybind11) or available as a submodule / include dir.
# ---------------------------------------------------------------------------
def _get_pybind11_include() -> str:
    try:
        import pybind11  # type: ignore
        return pybind11.get_include()
    except ImportError:
        # Fallback: assume standard site-packages layout
        site_packages = next(
            (p for p in sys.path if "site-packages" in p), ""
        )
        candidate = os.path.join(site_packages, "pybind11", "include")
        if os.path.isdir(candidate):
            return candidate
        raise RuntimeError(
            "pybind11 not found. Install it with: pip install pybind11"
        )


def _get_python_include() -> str:
    import sysconfig
    return sysconfig.get_path("include")


# Source file is in the same directory as this setup.py
HERE = Path(__file__).parent.resolve()
CPP_SOURCE = str(HERE / "matcher.cpp")

# Compiler flags tuned for C++17 and high-performance builds
EXTRA_COMPILE_ARGS: list[str]
if sys.platform == "win32":
    EXTRA_COMPILE_ARGS = ["/std:c++17", "/O2", "/EHsc"]
else:
    EXTRA_COMPILE_ARGS = [
        "-std=c++17",
        "-O3",
        "-march=native",
        "-ffast-math",
        "-DNDEBUG",
        "-fvisibility=hidden",   # Required for PyBind11 shared libs
    ]

matcher_native_ext = Extension(
    name="matcher_native",
    sources=[CPP_SOURCE],
    include_dirs=[
        _get_pybind11_include(),
        _get_python_include(),
    ],
    language="c++",
    extra_compile_args=EXTRA_COMPILE_ARGS,
)

setup(
    name="matcher_native",
    version="1.0.0",
    description="TRIDENT Native C++ Heuristic Matching Kernel (PyBind11)",
    author="TRIDENT Engineering",
    ext_modules=[matcher_native_ext],
    python_requires=">=3.10",
    zip_safe=False,
)
