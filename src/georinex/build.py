"""
build Hatanaka converter with only a C compiler
"""
import subprocess
import shutil
from pathlib import Path

R = Path(__file__).parent / 'rnxcmp'


def build(cc: str = None, src: Path = R / 'source/crx2rnx.c') -> int:
    # C compiler search order from mesonbuild/environment.py
    if cc:
        return do_compile(cc, src)

    compilers = ['icl', 'cl', 'cc', 'gcc', 'clang', 'clang-cl', 'pgcc']
    ret = 1
    for cc in compilers:
        if shutil.which(cc):
            ret = do_compile(cc, src)
            if ret == 0:
                break

    return ret


def do_compile(cc: str, src: Path) -> int:
    if cc.endswith('cl'):  # msvc-like
        cmd = [cc, str(src), '/Fe:'+str(R)]
    else:
        cmd = [cc, str(src), '-O2', '-o', str(R/'crx2rnx')]

    print(' '.join(cmd))
    ret = subprocess.run(cmd).returncode

    return ret
