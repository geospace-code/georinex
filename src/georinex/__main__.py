import argparse
from pathlib import Path
import numpy as np
from datetime import timedelta
import logging

import georinex as gr


def georinex_read():
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
    georinex_read ~/data/VEN100ITA_R_20181580000_01D_MN.rnx.gz
    georinex_read ~/data/ABMF00GLP_R_20181330000_01D_30S_MO.zip

    # read a limited range of time in a RINEX file
    georinex_read ~/data/PUMO00CR__R_20180010000_01D_15S_MO.rnx -t 2018-01-01 2018-01-01T00:30
    """
    p = argparse.ArgumentParser(description='example of reading RINEX 2/3 Navigation/Observation file')
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


def georinex_plot():
    """
    PyRINEX plotting example
    includes how to index by satellite, measurement type and time
    """

    import matplotlib.dates as md
    from matplotlib.pyplot import figure, show

    p = argparse.ArgumentParser(description='Plot raw Rinex data')
    p.add_argument('rinexfn', help='RINEX file to analyze')
    p.add_argument('sv', help='SVs to analyze e.g. G14 C12', nargs='+')
    p.add_argument('-t', '--tlim', help='time limits (start stop) e.g. 2017-05-25T12:47 2017-05-25T13:05', nargs=2)
    p.add_argument('-w', '--what', help='what measurements to plot e.g. L1C',
                   nargs='+', default=['L1C', 'P1'])
    P = p.parse_args()

    rinexfn = Path(P.rinexfn).expanduser()

    obs = gr.load(rinexfn, use='G')

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


def rinex2hdf5():
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

    p = argparse.ArgumentParser(description='example of reading RINEX 2/3 Navigation/Observation file')
    p.add_argument('indir', help='path to RINEX 2 or RINEX 3 files to convert')
    p.add_argument('glob', help='file glob pattern', nargs='?', default='*')
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
    P = p.parse_args()

    gr.batch_convert(P.indir, P.glob, P.out, use=P.use, tlim=P.tlim,
                     useindicators=P.useindicators, meas=P.meas,
                     verbose=P.verbose, fast=P.strict)


def georinex_time():
    p = argparse.ArgumentParser()
    p.add_argument('filename', help='RINEX filename to get times from')
    p.add_argument('-glob', help='file glob pattern', nargs='+', default='*')
    p.add_argument('-v', '--verbose', action='store_true')
    p = p.parse_args()

    filename = Path(p.filename).expanduser()

    print('filename: start, stop, number of times, interval')

    if filename.is_dir():
        flist = gr.globber(filename, p.glob)
        for f in flist:
            eachfile(f, p.verbose)
    elif filename.is_file():
        eachfile(filename, p.verbose)
    else:
        raise FileNotFoundError(f'{filename} is not a path or file')


def eachfile(fn: Path, verbose: bool = False):
    try:
        times = gr.gettime(fn)
    except Exception as e:
        if verbose:
            print(f'{fn.name}: {e}')
        return

# %% output
    Ntimes = times.size

    if Ntimes == 0:
        return

    ostr = (f"{fn.name}:"
            f" {times[0].isoformat()}"
            f" {times[-1].isoformat()}"
            f" {Ntimes}")

    hdr = gr.rinexheader(fn)
    interval = hdr.get('interval', np.nan)
    if ~np.isnan(interval):
        ostr += f" {interval}"
        Nexpect = (times[-1] - times[0]) // timedelta(seconds=interval) + 1
        if Nexpect != Ntimes:
            logging.warning(f'{fn.name}: expected {Nexpect} but got {Ntimes} times')

    print(ostr)

    if verbose:
        print(times)


def georinex_loc():
    """
    Visualize location of all receivers on map,
    where color & size are proportional to measurement interval (smaller is better)
    """
    from matplotlib.pyplot import show
    import georinex.plots_geo as grp
    import georinex.geo as gg

    p = argparse.ArgumentParser(description='plot receiver locations')
    p.add_argument('indir', help='path to RINEX 2 or RINEX 3 files')
    p.add_argument('-glob', help='file glob pattern', nargs='+',
                   default=['*o',
                            '*O.rnx', '*O.rnx.gz',
                            '*O.crx', '*O.crx.gz'])
    p = p.parse_args()

    indir = Path(p.indir).expanduser()

    flist = gr.globber(indir, p.glob)

    locs = gg.get_locations(flist)

    grp.receiver_locations(locs)

    show()
