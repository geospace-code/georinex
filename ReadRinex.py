#!/usr/bin/env python
"""
Reads RINEX 2/3 OBS/NAV files and plots.
Returns data as xarray.Dataset, think of it like an N-dimensional Numpy NDarray with lots of metadata and
very fancy indexing methods.
Xarray can be thought of as an analytically-tuned Pandas.

The RINEX version is automatically detected.  GZIP .gz files can be read directly as well.

Examples:

./ReadRinex.py ~/data/VEN100ITA_R_20181580000_01D_MN.rnx.gz

"""
from argparse import ArgumentParser
import xarray
import georinex as gr


def main():
    p = ArgumentParser(
        description='example of reading RINEX 2/3 Navigation/Observation file')
    p.add_argument('rinexfn', help='path to RINEX 2 or RINEX 3 file')
    p.add_argument('-o', '--outfn', help='write data as NetCDF4 file')
    p.add_argument('-q', '--quiet',
                   help='do not generate plots or print unneeded text (for HPC/cloud)',
                   action='store_true')
    p.add_argument('-use', help='select which GNSS system(s) to use',
                   nargs='+')
    P = p.parse_args()

    verbose = not P.quiet

    obs, nav = gr.readrinex(P.rinexfn, P.outfn, P.use, verbose)

# %% plots
    if verbose:
        plots(nav, obs)


def plots(nav: xarray.Dataset, obs: xarray.Dataset):
    from georinex.plots import plotnav, plotobs
    from matplotlib.pyplot import show

    try:
        plotnav(nav)
    except NameError:
        pass

    try:
        plotobs(obs)
    except NameError:
        pass

    show()


if __name__ == '__main__':
    main()
