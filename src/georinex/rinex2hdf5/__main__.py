"""
Converts RINEX 2/3 NAV/OBS to NetCDF4 / HDF5

The RINEX version is automatically detected.
Compressed RINEX files including:
    * GZIP .gz
    * ZIP .zip
    * LZW .Z
    * Hatanaka .crx / .crx.gz
are handled seamlessly via TextIO stream.

Examples:

# batch convert RINEX OBS2 to NetCDF4/HDF5
rnx2hdf5.py ~/data "*o"
rnx2hdf5.py ~/data "*o.Z"
rnx2hdf5.py ~/data "*o.zip"

# batch convert RINEX OBS3 to NetCDF4/HDF5
rnx2hdf5.py ~/data "*MO.rnx"
rnx2hdf5.py ~/data "*MO.rnx.gz"

# batch convert compressed Hatanaka RINEX files to NetCDF4 / HDF5
rnx2hdf5.py ~/data "*.crx.gz"
"""

import argparse

import georinex as gr


p = argparse.ArgumentParser(description="example of reading RINEX 2/3 Navigation/Observation file")
p.add_argument("indir", help="path to RINEX 2 or RINEX 3 files to convert")
p.add_argument("glob", help="file glob pattern", nargs="?", default="*")
p.add_argument("-o", "--out", help="write data to path or file as NetCDF4")
p.add_argument("-v", "--verbose", action="store_true")
p.add_argument("-p", "--plot", help="display plots", action="store_true")
p.add_argument("-u", "--use", help="select which GNSS system(s) to use", nargs="+")
p.add_argument("-m", "--meas", help="select which GNSS measurement(s) to use", nargs="+")
p.add_argument("-t", "--tlim", help="specify time limits (process part of file)", nargs=2)
p.add_argument(
    "-useindicators",
    help="use SSI, LLI indicators (signal, loss of lock)",
    action="store_true",
)
p.add_argument(
    "-strict",
    help="do not use speculative preallocation (slow) let us know if this is needed",
    action="store_false",
)
P = p.parse_args()

gr.batch_convert(
    P.indir,
    P.glob,
    P.out,
    use=P.use,
    tlim=P.tlim,
    useindicators=P.useindicators,
    meas=P.meas,
    verbose=P.verbose,
    fast=P.strict,
)
