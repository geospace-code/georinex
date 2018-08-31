import gzip
import zipfile
from pathlib import Path
import subprocess
from contextlib import contextmanager
import io
import os
from typing.io import TextIO
from typing import Union, Dict, Any
try:
    import unlzw
except ImportError:
    unlzw = None

R = Path(__file__).resolve().parents[1]


@contextmanager
def opener(fn: Path, header: bool=False, verbose: bool=False) -> TextIO:
    """provides file handle for regular ASCII or gzip files transparently"""
    if fn.is_dir():
        raise FileNotFoundError(f'{fn} is a directory; I need a file')

    if verbose:
        if fn.stat().st_size > 100e6:
            print(f'opening {fn.stat().st_size/1e6} MByte {fn.name}')

    if fn.suffixes == ['.crx', '.gz']:
        if header:
            with gzip.open(fn, 'rt') as f:
                yield f
        else:
            with gzip.open(fn, 'rt') as g:
                f = io.StringIO(_opencrx(g))
                yield f
    elif fn.suffix == '.crx':
        if header:
            with fn.open('r') as f:
                yield f
        else:
            with fn.open('r') as g:
                f = io.StringIO(_opencrx(g))
                yield f
    elif fn.suffix == '.gz':
        with gzip.open(fn, 'rt') as f:
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

    else:
        with fn.open('r') as f:
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

        if fn.suffixes == ['.crx', '.gz']:
            with gzip.open(fn, 'rt') as z:
                return rinexinfo(io.StringIO(z.read(80)))
        elif fn.suffix == '.crx':
            with fn.open('r') as f:
                return rinexinfo(io.StringIO(f.read(80)))
        else:
            with opener(fn) as f:
                return rinexinfo(f)

    try:
        line = f.readline(80)  # don't choke on binary files
        if not isinstance(line, str) or line[60:80] not in ('RINEX VERSION / TYPE', 'CRINEX VERS   / TYPE'):
            raise ValueError

        info = {'version': float(line[:9]),  # yes :9
                'filetype': line[20],
                'systems': line[40],
                'hatanaka': line[20:40] == 'COMPACT RINEX FORMAT'}

        if info['systems'] == ' ':
            if info['filetype'] == 'N' and int(info['version']) == 2:  # type: ignore
                info['systems'] = 'G'
            else:
                info['systems'] = info['filetype']

    except (ValueError, UnicodeDecodeError) as e:
        # keep ValueError for consistent user error handling
        raise ValueError(f'not a known/valid RINEX file.  {e}')

    return info
