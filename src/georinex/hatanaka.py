"""
handle Hatanka CRINEX files
"""
import subprocess
import shutil
from pathlib import Path
from typing.io import TextIO

from .build import build


def crxexe(path: Path = Path(__file__).parent / 'rnxcmp') -> str:
    """
    Determines if CRINEX converter is available.
    Don't use LRU_CACHE to allow for build-on-demand

    Parameters
    ----------
    path: pathlib.Path
        path to crx2rnx executable

    Returns
    -------
    exe: str
        fullpath to crx2rnx executable
    """
    exe = shutil.which('crx2rnx', path=str(path))
    if not exe:
        return None

    # crx2rnx -h:  returncode == 1
    ret = subprocess.run([exe, '-h'], stderr=subprocess.PIPE,
                         universal_newlines=True)

    if ret.stderr.startswith('Usage'):
        return exe
    else:
        return None


def opencrx(f: TextIO) -> str:
    """
    Conversion to string is necessary because of a quirk where gzip.open() even with 'rt' doesn't decompress until read.

    Nbytes is used to read first line.
    """
    exe = crxexe()

    if not exe:
        if build() != 0:
            raise RuntimeError('could not build Hatanka converter. Do you have a C compiler?')
        exe = crxexe()
        if not exe:
            raise RuntimeError('Hatanaka converter is broken or missing.')

    ret = subprocess.check_output([exe, '-'],
                                  input=f.read(),
                                  universal_newlines=True)

    return ret
