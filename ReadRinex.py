#!/usr/bin/env python
"""
Reads RINEX 2/3 OBS/NAV files and plots.
Returns data as xarray.Dataset, think of it like an N-dimensional Numpy NDarray with lots of metadata and
very fancy indexing methods.
Xarray can be thought of as an analytically-tuned Pandas.

The RINEX version is automatically detected.  GZIP .gz files can be read directly as well.

Examples:

./ReadRinex.py ~/data/VEN100ITA_R_20181580000_01D_MN.rnx.gz
./ReadRinex.py ~/data/ABMF00GLP_R_20181330000_01D_30S_MO.zip

./ReadRinex.py ~/data/PUMO00CR__R_20180010000_01D_15S_MO.rnx -t 2018-01-01 2018-01-01T00:30


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
                   help='do not generate plots or print unneeded text (for HPC/cloud)', action='store_true')
    p.add_argument('-u', '--use', help='select which GNSS system(s) to use', nargs='+')
    p.add_argument('-t', '--tlim', help='specify time limits (process part of file)', nargs=2)
    p.add_argument('-useindicators', help='use SSI, LLI indicators (signal, loss of lock)', action='store_true')
    P = p.parse_args()

    verbose = not P.quiet

    obs, nav = gr.readrinex(P.rinexfn, P.outfn, use=P.use, tlim=P.tlim,
                            useindicators=P.useindicators, verbose=verbose)

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
