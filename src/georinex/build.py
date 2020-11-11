"""
build Hatanaka converter with only a C compiler
"""
import subprocess
import shutil
from pathlib import Path

R = Path(__file__).parent / "rnxcmp"


def build(cc: str = None, src: Path = R / "source/crx2rnx.c") -> int:
    if cc:
        return do_compile(cc, src)

    compilers = ["cc", "gcc", "clang", "icc", "icl", "cl", "clang-cl"]
    ret = 1
    for cc in compilers:
        if shutil.which(cc):
            ret = do_compile(cc, src)
            if ret == 0:
                break

    return ret


def do_compile(cc: str, src: Path) -> int:
    if not src.is_file():
        raise FileNotFoundError(src)

    if cc.endswith("cl"):  # msvc-like
        cmd = [cc, str(src), f"/Fe:{R}"]
    else:
        cmd = [cc, str(src), "-O2", f"-o{R / 'crx2rnx'}"]

    print(" ".join(cmd))
    ret = subprocess.run(cmd).returncode

    return ret
