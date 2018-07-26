import gzip
import zipfile
from pathlib import Path
from contextlib import contextmanager
import io
from typing.io import TextIO
from typing import Union, Dict


@contextmanager
def opener(fn: Path):
    """provides file handle for regular ASCII or gzip files transparently"""
    if fn.suffix == '.gz':
        with gzip.open(fn, 'rt') as f:
            yield f
    elif fn.suffix == '.zip':
        with zipfile.ZipFile(fn, 'r') as z:  # type: ignore
            flist = z.namelist()
            for rinexfn in flist:
                with z.open(rinexfn, 'r') as bf:
                    f = io.TextIOWrapper(bf, newline=None)
                    yield f
    else:
        with fn.open('r') as f:
            yield f


def rinexinfo(f: Union[Path, TextIO]) -> Dict[str, Union[str, float]]:
    """verify RINEX version"""
    if isinstance(f, (str, Path)):
        fn = Path(f).expanduser()

        with opener(fn) as f:
            return rinexinfo(f)

    line = f.readline()

    info = {'version': float(line[:9]),  # yes :9
            'filetype': line[20]}

    return info
