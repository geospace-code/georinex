#!/usr/bin/env python
"""
Reads RINEX 2/3 OBS/NAV file and plot (or convert to NetCDF4 / HDF5).
Returns data as xarray.Dataset, think of it like an N-dimensional Numpy NDarray with lots of metadata and
very fancy indexing methods.
Xarray can be thought of as an analytically-tuned Pandas.

The RINEX version is automatically detected.
Compressed RINEX files including:
    * GZIP .gz
    * ZIP .zip
    * LZW .Z
    * Hatanaka .crx / .crx.gz
are handled seamlessly via TextIO stream.

Examples:

# read RINEX files (NAV/OBS, Rinex 2 or 3, Hatanaka, etc.)
./ReadRinex.py ~/data/VEN100ITA_R_20181580000_01D_MN.rnx.gz
./ReadRinex.py ~/data/ABMF00GLP_R_20181330000_01D_30S_MO.zip

# read a limited range of time in a RINEX file
./ReadRinex.py ~/data/PUMO00CR__R_20180010000_01D_15S_MO.rnx -t 2018-01-01 2018-01-01T00:30

"""
from argparse import ArgumentParser
import georinex as gr


def main():
    p = ArgumentParser(description='example of reading RINEX 2/3 Navigation/Observation file')
    p.add_argument('rinexfn', help='path to RINEX 2 or RINEX 3 file')
    p.add_argument('-o', '--out', help='write data to path or file as NetCDF4')
    p.add_argument('-v', '--verbose', action='store_true')
    p.add_argument('-p', '--plot', help='display plots', action='store_true')
    p.add_argument('-u', '--use', help='select which GNSS system(s) to use', nargs='+')
    p.add_argument('-m', '--meas', help='select which GNSS measurement(s) to use', nargs='+')
    p.add_argument('-t', '--tlim', help='specify time limits (process part of file)', nargs=2)
    p.add_argument('-useindicators', help='use SSI, LLI indicators (signal, loss of lock)',
                   action='store_true')
    p.add_argument('-strict', help='do not use speculative preallocation (slow) let us know if this is needed',
                   action='store_false')
    p.add_argument('-interval', help='read the rinex file only every N seconds', type=float)
    P = p.parse_args()

    data = gr.load(P.rinexfn, P.out, use=P.use, tlim=P.tlim,
                   useindicators=P.useindicators, meas=P.meas,
                   verbose=P.verbose, fast=P.strict, interval=P.interval)
# %% plots
    if P.plot:
        import georinex.plots as grp
        from matplotlib.pyplot import show

        grp.timeseries(data)
        show()
    else:
        print(data)


if __name__ == '__main__':
    main()
