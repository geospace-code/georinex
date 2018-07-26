#!/usr/bin/env python
"""
print out start, stop (or all) times in RINEX file
"""
from argparse import ArgumentParser
import georinex as gr


def main():
    p = ArgumentParser()
    p.add_argument('filename', help='RINEX filename to get times from')
    p.add_argument('-v', '--verbose', help='print all times instead of just start, stop', action='store_true')
    p = p.parse_args()

    times = gr.gettime(p.filename)

    if p.verbose:
        print('\n'.join(map(str, times)))
    else:
        print(times[0])
        print(times[-1])


if __name__ == '__main__':
    main()
