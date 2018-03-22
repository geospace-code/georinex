from __future__ import division  # absolutely needed for Py27 strange behavior
try:
    from pathlib import Path
    Path().expanduser()
except (ImportError,AttributeError):
    from pathlib2 import Path
#
import logging
import xarray
from time import time
#
from .rinex2 import _rinexnav2, _scan2
from .rinex3 import _rinexnav3, _scan3

COMPLVL = 1  # for NetCDF compression. too high slows down with little space savings.

def getRinexVersion(fn):
    fn = Path(fn).expanduser()

    with fn.open('r') as f:
        """verify RINEX version"""
        line = f.readline()
        return float(line[:9])

#%% Navigation file
def rinexnav(fn, ofn=None, group='NAV'):

    fn = Path(fn).expanduser()
    if fn.suffix=='.nc':
        try:
            return xarray.open_dataset(fn, group=group)
        except OSError:
            logging.error('Group {} not found in {}'.format(group,fn))
            return

    ver = getRinexVersion(fn)
    if int(ver) == 2:
        nav =  _rinexnav2(fn)
    elif int(ver) == 3:
        nav = _rinexnav3(fn)
    else:
        raise ValueError('unknown RINEX verion {}  {}'.format(ver,fn))

    if ofn:
        ofn = Path(ofn).expanduser()
        print('saving NAV data to',ofn)
        wmode='a' if ofn.is_file() else 'w'
        nav.to_netcdf(ofn, group=group, mode=wmode)

    return nav

# %% Observation File
def rinexobs(fn, ofn=None, use=None, group='OBS',verbose=False):
    """
    Program overviw:
    1) scan the whole file for the header and other information using scan(lines)
    2) each epoch is read

    rinexobs() returns the data in an xarray.Dataset
    """

    fn = Path(fn).expanduser()
    if fn.suffix=='.nc':
        try:
            return xarray.open_dataset(fn, group=group)
        except OSError:
            logging.error('Group {} not found in {}'.format(group,fn))
            return



    tic = time()
    ver = getRinexVersion(fn)
    if int(ver) == 2:
        obs = _scan2(fn, verbose)
    elif int(ver) == 3:
        obs = _scan3(fn, use, verbose)
    else:
        raise ValueError('unknown RINEX verion {}  {}'.format(ver,fn))
        print("finished in {:.2f} seconds".format(time()-tic))


    if ofn:
        ofn = Path(ofn).expanduser()
        print('saving OBS data to',ofn)
        wmode='a' if ofn.is_file() else 'w'

        enc = {k:{'zlib':True,'complevel':COMPLVL,'fletcher32':True} for k in obs.data_vars}
        obs.to_netcdf(ofn, group=group, mode=wmode,encoding=enc)

    return obs


