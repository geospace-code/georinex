#!/usr/bin/env python
"""
Reads RINEX 2/3 OBS/NAV files and plots.
Returns data as xarray.Dataset, think of it like an N-dimensional Numpy NDarray with lots of metadata and
very fancy indexing methods.
Xarray can be thought of as an analytically-tuned Pandas.

The RINEX version is automatically detected.
Compressed RINEX files including:
    * GZIP .gz
    * ZIP .zip
    * LZW .Z
are handled seamlessly via TextIO stream.

Examples:

./ReadRinex.py ~/data/VEN100ITA_R_20181580000_01D_MN.rnx.gz
./ReadRinex.py ~/data/ABMF00GLP_R_20181330000_01D_30S_MO.zip

./ReadRinex.py ~/data/PUMO00CR__R_20180010000_01D_15S_MO.rnx -t 2018-01-01 2018-01-01T00:30

"""
from pathlib import Path
from argparse import ArgumentParser
import georinex as gr
import georinex.plots as grp
try:
    from matplotlib.pyplot import show
except ImportError:
    show = None


def main():
    p = ArgumentParser(description='example of reading RINEX 2/3 Navigation/Observation file')
    p.add_argument('rinexfn', help='path to RINEX 2 or RINEX 3 file')
    p.add_argument('-g', '--glob', help='file glob pattern', default='*')
    p.add_argument('-o', '--outfn', help='write data as NetCDF4 file')
    p.add_argument('-q', '--quiet', help='do not generate plots or print unneeded text (for HPC/cloud)',
                   action='store_true')
    p.add_argument('-u', '--use', help='select which GNSS system(s) to use', nargs='+')
    p.add_argument('-m', '--meas', help='select which GNSS measurement(s) to use', nargs='+')
    p.add_argument('-t', '--tlim', help='specify time limits (process part of file)', nargs=2)
    p.add_argument('-useindicators', help='use SSI, LLI indicators (signal, loss of lock)',
                   action='store_true')
    P = p.parse_args()

    verbose = not P.quiet

    fn = Path(P.rinexfn).expanduser()

    if fn.is_file():
        data = gr.load(P.rinexfn, P.outfn, use=P.use, tlim=P.tlim,
                       useindicators=P.useindicators, meas=P.meas, verbose=verbose)
    elif fn.is_dir():
        flist = [f for f in fn.glob(P.glob) if f.is_file()]
        for f in flist:
            try:
                data = gr.load(f, P.outfn, use=P.use, tlim=P.tlim,
                               useindicators=P.useindicators, meas=P.meas, verbose=verbose)
            except Exception as e:
                print(f'{f.name}: {e}')
                continue

            if verbose:
                grp.timeseries(data)
    else:
        raise FileNotFoundError(f'{fn} is not a path or file')
# %% plots
    if verbose and show is not None:
        grp.timeseries(data)
        show()


if __name__ == '__main__':
    main()
