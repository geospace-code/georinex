from pathlib import Path
import logging
import xarray
from typing import Union, Tuple
from datetime import datetime
#
from .io import opener
from .rinex2 import rinexnav2, _scan2
from .rinex3 import rinexnav3, _scan3

# for NetCDF compression. too high slows down with little space savings.
COMPLVL = 1


def readrinex(rinexfn: Path, outfn: Path=None,
              use: Union[str, list, tuple]=None,
              tlim: Union[None, Tuple[datetime, datetime]]=None,
              verbose: bool=True) -> xarray.Dataset:
    """
    Reads OBS, NAV in RINEX 2,3.  Plain ASCII text or GZIP .gz.
    """
    nav = None
    obs = None
    rinexfn = Path(rinexfn).expanduser()
# %% detect type of Rinex file
    if rinexfn.suffix in ('.gz', '.zip'):
        fnl = rinexfn.stem.lower()
    else:
        fnl = rinexfn.name.lower()

    if fnl.endswith('n') or fnl.endswith('n.rnx'):
        nav = rinexnav(rinexfn, outfn)
    elif fnl.endswith('o') or fnl.endswith('o.rnx'):
        obs = rinexobs(rinexfn, outfn, use=use, verbose=verbose)
    elif fnl.endswith('.crx'):
        raise NotImplementedError('Hatanaka compressed RINEX is not yet supported')
    elif rinexfn.suffix.endswith('.nc'):
        nav = rinexnav(rinexfn)
        obs = rinexobs(rinexfn)
    else:
        raise ValueError(f"I dont know what type of file you're trying to read: {rinexfn}")

    return obs, nav


def getRinexVersion(fn: Path) -> float:
    """verify RINEX version"""
    fn = Path(fn).expanduser()

    with opener(fn) as f:
        ver = float(f.readline()[:9])  # yes :9

    return ver
# %% Navigation file


def rinexnav(fn: Path, ofn: Path=None, group: str='NAV') -> xarray.Dataset:
    """ Read RINEX 2,3  NAV files in ASCII or GZIP"""
    fn = Path(fn).expanduser()
    if fn.suffix == '.nc':
        try:
            return xarray.open_dataset(fn, group=group)
        except OSError:
            logging.error(f'Group {group} not found in {fn}')
            return

    ver = getRinexVersion(fn)
    if int(ver) == 2:
        nav = rinexnav2(fn)
    elif int(ver) == 3:
        nav = rinexnav3(fn)
    else:
        raise ValueError(f'unknown RINEX verion {ver}  {fn}')

    if ofn:
        ofn = Path(ofn).expanduser()
        print('saving NAV data to', ofn)
        wmode = 'a' if ofn.is_file() else 'w'
        nav.to_netcdf(ofn, group=group, mode=wmode)

    return nav

# %% Observation File


def rinexobs(fn: Path, ofn: Path=None,
             use: Union[str, list, tuple]=None,
             group: str='OBS',
             tlim: Union[None, Tuple[datetime, datetime]]=None,
             verbose: bool=False) -> xarray.Dataset:
    """
    Read RINEX 2,3 OBS files in ASCII or GZIP
    """

    fn = Path(fn).expanduser()
    if fn.suffix == '.nc':
        try:
            logging.debug(f'loading {fn} with xarray')
            return xarray.open_dataset(fn, group=group)
        except OSError:
            logging.error(f'Group {group} not found in {fn}')
            return
# %% version selection
    ver = getRinexVersion(fn)

    if int(ver) == 2:
        obs = _scan2(fn, use, tlim=tlim, verbose=verbose)
    elif int(ver) == 3:
        obs = _scan3(fn, use, tlim=tlim, verbose=verbose)
    else:
        raise ValueError(f'unknown RINEX verion {ver}  {fn}')
# %% optional output write
    if ofn:
        ofn = Path(ofn).expanduser()
        print('saving OBS data to', ofn)
        wmode = 'a' if ofn.is_file() else 'w'

        enc = {k: {'zlib': True, 'complevel': COMPLVL, 'fletcher32': True}
               for k in obs.data_vars}
        obs.to_netcdf(ofn, group=group, mode=wmode, encoding=enc)

    return obs
