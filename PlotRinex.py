#!/usr/bin/env python
"""
PyRINEX plotting example

includes how to index by satellite, measurement type and time
"""
from argparse import ArgumentParser
from pathlib import Path
import numpy as np
import georinex as gr
import matplotlib.dates as md
from matplotlib.pyplot import figure, show


def main():
    p = ArgumentParser(description='Plot raw Rinex data')
    p.add_argument('rinexfn', help='RINEX file to analyze')
    p.add_argument('sv', help='SVs to analyze e.g. G14 C12', nargs='+')
    p.add_argument('-t', '--tlim', help='time limits (start stop) e.g. 2017-05-25T12:47 2017-05-25T13:05', nargs=2)
    p.add_argument('-w', '--what', help='what measurements to plot e.g. L1C',
                   nargs='+', default=['L1C', 'P1'])
    P = p.parse_args()

    rinexfn = Path(P.rinexfn).expanduser()

    obs, nav = gr.readrinex(rinexfn, use='G')

# %% optional time indexing demo
    # can use datetime or string

    # boolean indexing  -- set "i=slice(None)" to disable time indexing.
    if P.tlim is not None:
        i = (obs.time >= np.datetime64(P.tlim[0])) & (obs.time <= np.datetime64(P.tlim[1]))
    else:
        i = slice(None)
# %% plot
    SV = P.sv
    what = P.what
    # FIXME: make these title automatic based on requested measurement?
    # titles = ['Psedoranges of GPS and Glonass', 'Carrier Phase', 'Doppler', 'Signal Strength']
    # ylabels = ['Pseudoranges', 'Phase', 'Doppler', 'signal strength']

    fg = figure(figsize=(9, 9))
    axs = fg.subplots(4, 1, sharex=True)

    for v, title, ylabel, ax in zip(what, axs):

        if v not in obs:
            continue

        Satobs = obs[v][i].sel(sv=SV).dropna(dim='time', how='all')

        Satobs.plot(ax=ax)

        ax.set_title(title)
        ax.set_ylabel(ylabel)
        ax.legend(loc='center left', bbox_to_anchor=(1, 0.5))

    axs[-1].set_xlabel('Time [UTC]')
    axs[-1].xaxis.set_major_formatter(md.DateFormatter('%Y-%m-%dT%H:%M'))
    fg.suptitle(f'{rinexfn.name}  satellite {SV}')

    show()


if __name__ == '__main__':
    main()
