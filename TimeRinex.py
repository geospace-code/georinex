#!/usr/bin/env python
"""
print out start, stop (or all) times in RINEX file
"""
from pathlib import Path
from argparse import ArgumentParser
import georinex as gr


def main():
    p = ArgumentParser()
    p.add_argument('filename', help='RINEX filename to get times from')
    p.add_argument('glob', help='file glob pattern', nargs='?', default='*')
    p.add_argument('-v', '--verbose', action='store_true')
    p.add_argument('-q', '--quiet', help='dont print errors, just times', action='store_true')
    p = p.parse_args()

    filename = Path(p.filename).expanduser()

    print('filename: start, stop, interval')

    if filename.is_dir():
        flist = [f for f in filename.glob(p.glob) if f.is_file()]
        for f in flist:
            eachfile(f, p.quiet, p.verbose)
    elif filename.is_file():
        eachfile(filename, p.quiet, p.verbose)
    else:
        raise FileNotFoundError(f'{filename} is not a path or file')


def eachfile(fn: Path, quiet: bool=False, verbose: bool=False):
    try:
        times = gr.gettime(fn)
    except Exception as e:
        if not quiet:
            print(f'{fn.name}: {e}')
        return
# %% output
    print(f"{fn.name}:"
          f" {times[0].values.astype('datetime64[us]').item().isoformat()}"
          f" {times[-1].values.astype('datetime64[us]').item().isoformat()}"
          f" {times.interval}")

    if verbose:
        print(times)


if __name__ == '__main__':
    main()
