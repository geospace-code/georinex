import gzip
import zipfile
from pathlib import Path
from contextlib import contextmanager
import io


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
#
#        with zipfile.ZipFile(fn, 'r') as z:
#            flist = z.namelist()
#            assert len(flist) == 1, f'which filename {flist} do you want from {fn}'
#            with z.open(flist[0], 'r') as f:
#                yield f
