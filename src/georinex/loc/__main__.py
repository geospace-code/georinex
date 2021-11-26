"""
Visualize location of all receivers on map,
where color & size are proportional to measurement interval (smaller is better)
"""

import argparse
from pathlib import Path

from matplotlib.pyplot import show

import georinex.plots_geo as grp
import georinex.geo as gg
import georinex as gr

p = argparse.ArgumentParser(description="plot receiver locations")
p.add_argument("indir", help="path to RINEX 2 or RINEX 3 files")
p.add_argument(
    "-glob",
    help="file glob pattern",
    nargs="+",
    default=["*o", "*O.rnx", "*O.rnx.gz", "*O.crx", "*O.crx.gz"],
)
p = p.parse_args()

indir = Path(p.indir).expanduser()

flist = gr.globber(indir, p.glob)

locs = gg.get_locations(flist)

grp.receiver_locations(locs)

show()
