#!/usr/bin/env python
"""
PyRINEX plotting example
"""
from pathlib import Path
import pyrinex as pr
import matplotlib.dates as md
from matplotlib.pyplot import figure, show

fn = Path('~/data/GEOP107Q.18o')

obs, nav = pr.readrinex(fn, use='G')

# %% plot
SV = 'G14'
titles = ['Psedoranges of GPS and Glonass', 'Carrier Phase', 'Doppler', 'Signal Strength']
ylabels = ['Pseudoranges', 'Phase', 'Doppler', 'signal strength']

fg = figure(figsize=(9, 9))
axs = fg.subplots(4, 1, sharex=True)

for v, title, ylabel, ax in zip(('C1C', 'L1C', 'D1C', 'S1C'), titles, ylabels, axs):

    if v not in obs:
        continue

    Satobs = obs[v].sel(sv=SV).dropna(dim='time', how='all')

    Satobs.plot(ax=ax)

    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.legend(loc='center left', bbox_to_anchor=(1, 0.5))

axs[-1].set_xlabel('Time [UTC]')
axs[-1].xaxis.set_major_formatter(md.DateFormatter('%Y-%m-%dT%H:%M'))
fg.suptitle(f'{fn.name}  satellite {SV}')


show()
