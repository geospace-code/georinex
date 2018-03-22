#!/usr/bin/env python
from matplotlib.pyplot import show
#
from pyrinex import rinexnav,rinexobs
from pyrinex.plots import plotnav, plotobs

if __name__ == '__main__':
    from argparse import ArgumentParser
    p = ArgumentParser(description='example of reading RINEX 2/3 Navigation/Observation file')
    p.add_argument('rinexfn',help='path to RINEX 2 or RINEX 3 file')
    p.add_argument('-o','--outfn',help='write data as NetCDF4 file')
    p.add_argument('--maxtimes',help='Choose to read only the first N INTERVALs of OBS file',type=int)
    p = p.parse_args()

    rinexfn = p.rinexfn
    if rinexfn.lower().endswith('n'):
        nav = rinexnav(rinexfn, p.outfn)

        plotnav(nav)
    elif rinexfn.lower().endswith('o'):
        obs = rinexobs(rinexfn, p.outfn)

        plotobs(obs)
    #%% TEC can be made another column (on the last axis) of the blocks array.
    else:
        raise ValueError("I dont know what type of file you're trying to read: {}".format(p.rinexfn))

    show()
