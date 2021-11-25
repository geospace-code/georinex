"""
build Hatanaka converter with only a C compiler
"""

import subprocess
import shutil
import os
from pathlib import Path


def build(src: Path, exe: Path, cc: str = None) -> int:
    """
    build an executable using one of several compilers
    """
    if cc:
        return do_compile(cc, src, exe)

    compilers = ["cc", "gcc", "clang", "icx", "icc", "nvcc"]
    if os.name == "nt":
        compilers.extend(["icl", "cl", "clang-cl"])

    ret = 1
    for cc in compilers:
        if shutil.which(cc):
            ret = do_compile(cc, src, exe)
            if ret == 0:
                break

    return ret


def do_compile(cc: str, src: Path, exe: Path) -> int:
    if not src.is_file():
        raise FileNotFoundError(src)

    cmd = [cc, str(src)]
    if cc.endswith("cl"):  # msvc-like
        cmd.append(f"/Fe:{exe}")
    else:
        cmd.extend(["-O2", f"-o{exe}"])

    print(" ".join(cmd))
    ret = subprocess.run(cmd).returncode

    return ret
