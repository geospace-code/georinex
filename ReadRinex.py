#!/usr/bin/env python
from pyrinex import rinexnav,rinexobs
from pyrinex.plots import plotnav, plotobs

if __name__ == '__main__':
    from argparse import ArgumentParser
    p = ArgumentParser(description='example of reading RINEX 2/3 Navigation/Observation file')
    p.add_argument('rinexfn',help='path to RINEX 2 or RINEX 3 file')
    p.add_argument('-o','--outfn',help='write data as NetCDF4 file')
    p.add_argument('-q','--quiet',help='do not generate plots or print unneeded text (for HPC/cloud)',action='store_true')
    p.add_argument('-use',help='select which GNSS systems to use (for now, GPS only)',nargs='+',default='G')
    p = p.parse_args()

    verbose = not p.quiet

    rinexfn = p.rinexfn
    if rinexfn.lower().endswith('n') or rinexfn.lower().endswith('n.rnx'):
        nav = rinexnav(rinexfn, p.outfn)
    elif rinexfn.lower().endswith('o') or rinexfn.lower().endswith('o.rnx'):
        obs = rinexobs(rinexfn, p.outfn, use=p.use, verbose=verbose)
    elif rinexfn.lower().endswith('.nc'):
        nav = rinexnav(rinexfn)
        obs = rinexobs(rinexfn)
    else:
        raise ValueError("I dont know what type of file you're trying to read: {}".format(p.rinexfn))

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
