#!/usr/bin/env python
import pyrinex as pr
import pyrinex.keplerian as kpr
from pyrinex.plots import plotnav, plotobs, plotsat

if __name__ == '__main__':
    from argparse import ArgumentParser
    p = ArgumentParser(description='example of reading RINEX 2/3 Navigation/Observation file')
    p.add_argument('rinexfn',help='path to RINEX 2 or RINEX 3 file')
    p.add_argument('-o','--outfn',help='write data as NetCDF4 file')
    p.add_argument('-q','--quiet',help='do not generate plots or print unneeded text (for HPC/cloud)',action='store_true')
    p.add_argument('-use',help='select which GNSS system(s) to use',nargs='+')
    p = p.parse_args()

    verbose = not p.quiet

    obs,nav = pr.readrinex(p.rinexfn, p.outfn, p.use, verbose)

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

# %% get satellites ECEF position vs. time
        # this has not been verified!
        try:
            ecef = kpr.keplerian2ecef(nav)
            plotsat(ecef)
        except Exception:
            pass

        show()
