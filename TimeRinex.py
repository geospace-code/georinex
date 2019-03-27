#!/usr/bin/env python
"""
print out start, stop (or all) times in RINEX file
"""
from pathlib import Path
from argparse import ArgumentParser
import georinex as gr
import numpy as np


def main():
    p = ArgumentParser()
    p.add_argument('filename', help='RINEX filename to get times from')
    p.add_argument('-glob', help='file glob pattern', nargs='+', default='*')
    p.add_argument('-v', '--verbose', action='store_true')
    p = p.parse_args()

    filename = Path(p.filename).expanduser()

    print('filename: start, stop, interval')

    if filename.is_dir():
        flist = gr.globber(filename, p.glob)
        for f in flist:
            eachfile(f, p.verbose)
    elif filename.is_file():
        eachfile(filename, p.quiet, p.verbose)
    else:
        raise FileNotFoundError(f'{filename} is not a path or file')


def eachfile(fn: Path, verbose: bool = False):
    try:
        times = gr.gettime(fn)
    except Exception as e:
        if verbose:
            print(f'{fn.name}: {e}')
        return

# %% output
    try:
        ostr = (f"{fn.name}:"
                f" {times[0].isoformat()}"
                f" {times[-1].isoformat()}")
    except IndexError:
        return

    try:
        if ~np.isnan(times.interval):
            ostr += f" {times.interval}"
    except AttributeError:
        pass

    print(ostr)

    if verbose:
        print(times)


if __name__ == '__main__':
    main()
