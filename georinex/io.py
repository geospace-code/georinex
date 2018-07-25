import gzip
from pathlib import Path
from contextlib import contextmanager


@contextmanager
def opener(fn: Path):
    """provides file handle for regular ASCII or gzip files transparently"""
    if fn.suffix == '.gz':
        with gzip.open(fn, 'rt') as f:
            yield f
    else:
        with fn.open('r') as f:
            yield f
