import gzip
import zipfile
from pathlib import Path
import subprocess
from contextlib import contextmanager
import io
from typing.io import TextIO
from typing import Union, Dict
try:
    import unlzw
except ImportError:
    unlzw = None


@contextmanager
def opener(fn: Path) -> TextIO:
    """provides file handle for regular ASCII or gzip files transparently"""
    if fn.is_dir():
        raise FileNotFoundError(f'{fn} is a directory; I need a file')

    if fn.suffixes == ['.crx', '.gz']:
        with gzip.open(fn, 'rt') as g:
            f: TextIO = io.StringIO(_opencrx(g))
            yield f
    elif fn.suffix == '.crx':
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
    try:
        In = f.read()
        ret = subprocess.check_output(['crx2rnx', '-'], input=In, universal_newlines=True)
    except subprocess.CalledProcessError as e:
        raise OSError(f'trouble converting Hatanka file, did you compile the crx2rnx program?   {e}')

    return ret


def rinexinfo(f: Union[Path, TextIO]) -> Dict[str, Union[str, float]]:
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
        line = f.readline()

        info = {'version': float(line[:9]),  # yes :9
                'filetype': line[20],
                'systems': line[40],
                'hatanaka': line[20:40] == 'COMPACT RINEX FORMAT'}

        if info['filetype'] == 'N' and int(info['version']) == 2 and info['systems'] == ' ':
            info['systems'] = 'G'

    except (ValueError, UnicodeDecodeError) as e:
        raise OSError(f'{f.name} does not appear to be a known/valid RINEX file.  {e}')

    return info
