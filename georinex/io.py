import gzip
import zipfile
from pathlib import Path
import subprocess
from contextlib import contextmanager
import io
import os
from typing.io import TextIO
from typing import Union, Dict, Any
from .common import rinex_version

try:
    import unlzw
except ImportError:
    unlzw = None

R = Path(__file__).resolve().parents[1]


@contextmanager
def opener(fn: Union[TextIO, Path],
           header: bool = False,
           verbose: bool = False) -> TextIO:
    """provides file handle for regular ASCII or gzip files transparently"""
    if isinstance(fn, str):
        fn = Path(fn).expanduser()

    if isinstance(fn, io.StringIO):
        yield fn
    else:
        if verbose:
            if fn.stat().st_size > 100e6:
                print(f'opening {fn.stat().st_size/1e6} MByte {fn.name}')

        if fn.suffix == '.gz':
            with gzip.open(fn, 'rt') as f:
                version, is_crinex = rinex_version(f.readline(80))
                f.seek(0)

                if is_crinex:
                    f = io.StringIO(_opencrx(f))
                yield f
        elif fn.suffix == '.zip':
            with zipfile.ZipFile(fn, 'r') as z:
                flist = z.namelist()
                for rinexfn in flist:
                    with z.open(rinexfn, 'r') as bf:
                        f = io.TextIOWrapper(bf, newline=None)
                        yield f
        elif fn.suffix == '.Z':
            if unlzw is None:
                raise ImportError('pip install unlzw')
            with fn.open('rb') as zu:
                with io.StringIO(unlzw.unlzw(zu.read()).decode('ascii')) as f:
                    yield f

        else:  # assume not compressed (or Hatanaka)
            with fn.open('r') as f:
                version, is_crinex = rinex_version(f.readline(80))
                f.seek(0)

                if is_crinex:
                    f = io.StringIO(_opencrx(f))
                yield f


def _opencrx(f: TextIO) -> str:
    """
    Conversion to string is necessary because of a quirk where gzip.open() even with 'rt' doesn't decompress until read.

    Nbytes is used to read first line.
    """
    exe = './crx2rnx'
    shell = False
    if os.name == 'nt':
        exe = exe[2:]
        shell = True

    try:
        In = f.read()
        ret = subprocess.check_output([exe, '-'], input=In,
                                      universal_newlines=True, cwd=R/'rnxcmp', shell=shell)
    except FileNotFoundError as e:
        raise FileNotFoundError(f'trouble converting Hatanka file, did you compile the crx2rnx program?   {e}')

    return ret


def rinexinfo(f: Union[Path, TextIO]) -> Dict[str, Any]:
    """verify RINEX version"""

    if isinstance(f, (str, Path)):
        fn = Path(f).expanduser()

        with opener(fn) as f:
            return rinexinfo(f)
    elif isinstance(f, io.StringIO):
        f.seek(0)

    try:
        line = f.readline(80)  # don't choke on binary files

        version = rinex_version(line)[0]

        file_type = line[20]
        if int(version) == 2:
            if file_type == 'N':
                system = 'G'
            elif file_type == 'G':
                system = 'R'
            elif file_type == 'E':
                system = 'E'
            else:
                system = line[40]
        else:
            system = line[40]

        if line[20] in ('O', 'C'):
            rinex_type = 'obs'
        elif line[20] == 'N' or 'NAV' in line[20:40]:
            rinex_type = 'nav'
        else:
            rinex_type = line[20]

        info = {'version': version,
                'filetype': file_type,
                'rinextype': rinex_type,
                'systems': system}

    except (TypeError, AttributeError, ValueError, UnicodeDecodeError) as e:
        # keep ValueError for consistent user error handling
        raise ValueError(f'not a known/valid RINEX file.  {e}')

    return info
