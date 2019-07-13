#!/usr/bin/env python
"""
print out start, stop (or all) times in RINEX file
"""
from pathlib import Path
from argparse import ArgumentParser
import georinex as gr
import logging
import numpy as np
from datetime import timedelta


def main():
    p = ArgumentParser()
    p.add_argument('filename', help='RINEX filename to get times from')
    p.add_argument('-glob', help='file glob pattern', nargs='+', default='*')
    p.add_argument('-v', '--verbose', action='store_true')
    p = p.parse_args()

    filename = Path(p.filename).expanduser()

    print('filename: start, stop, number of times, interval')

    if filename.is_dir():
        flist = gr.globber(filename, p.glob)
        for f in flist:
            eachfile(f, p.verbose)
    elif filename.is_file():
        eachfile(filename, p.verbose)
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
    Ntimes = times.size

    if Ntimes == 0:
        return

    ostr = (f"{fn.name}:"
            f" {times[0].isoformat()}"
            f" {times[-1].isoformat()}"
            f" {Ntimes}")

    hdr = gr.rinexheader(fn)
    interval = hdr.get('interval', np.nan)
    if ~np.isnan(interval):
        ostr += f" {interval}"
        Nexpect = (times[-1] - times[0]) // timedelta(seconds=interval) + 1
        if Nexpect != Ntimes:
            logging.warning(f'{fn.name}: expected {Nexpect} but got {Ntimes} times')

    print(ostr)

    if verbose:
        print(times)


if __name__ == '__main__':
    main()
