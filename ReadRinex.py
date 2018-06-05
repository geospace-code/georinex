#!/usr/bin/env python
import pyrinex as pr
from pyrinex.plots import plotnav, plotobs

if __name__ == '__main__':
    from argparse import ArgumentParser
    p = ArgumentParser(
        description='example of reading RINEX 2/3 Navigation/Observation file')
    p.add_argument('rinexfn', help='path to RINEX 2 or RINEX 3 file')
    p.add_argument('-o', '--outfn', help='write data as NetCDF4 file')
    p.add_argument(
        '-q', '--quiet', help='do not generate plots or print unneeded text (for HPC/cloud)', action='store_true')
    p.add_argument(
        '-use', help='select which GNSS system(s) to use', nargs='+')
    P = p.parse_args()

    verbose = not P.quiet

    obs, nav = pr.readrinex(P.rinexfn, P.outfn, P.use, verbose)

# %% plots
    if verbose:
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
