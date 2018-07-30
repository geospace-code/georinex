from pathlib import Path
import logging
import xarray
from typing import Union, Tuple, Dict, Any, Optional
from datetime import datetime
from dateutil.parser import parse
#
from .io import rinexinfo
from .obs2 import rinexobs2, obsheader2, gettime2
from .obs3 import rinexobs3, obsheader3, gettime3
from .nav2 import rinexnav2, navheader2
from .nav3 import rinexnav3, navheader3

# for NetCDF compression. too high slows down with little space savings.
COMPLVL = 1


def readrinex(rinexfn: Path, outfn: Path=None,
              use: Union[str, list, tuple]=None,
              tlim: Tuple[datetime, datetime]=None,
              useindicators: bool=False,
              verbose: bool=True) -> xarray.Dataset:
    """
    Reads OBS, NAV in RINEX 2,3.  Plain ASCII text or GZIP .gz.
    """
    nav = None
    obs = None
    rinexfn = Path(rinexfn).expanduser()
# %% detect type of Rinex file
    rtype = rinextype(rinexfn)

    if rtype == 'nav':
        nav = rinexnav(rinexfn, outfn, tlim=tlim)
    elif rtype == 'obs':
        obs = rinexobs(rinexfn, outfn, use=use, tlim=tlim, useindicators=useindicators, verbose=verbose)
    elif rtype == 'nc':
        nav = rinexnav(rinexfn)
        obs = rinexobs(rinexfn)
    else:
        raise ValueError(f"I dont know what type of file you're trying to read: {rinexfn}")

    return obs, nav
# %% Navigation file


def rinexnav(fn: Path, ofn: Path=None, group: str='NAV',
             tlim: Tuple[datetime, datetime]=None) -> xarray.Dataset:
    """ Read RINEX 2 or 3  NAV files"""
    fn = Path(fn).expanduser()
    if fn.suffix == '.nc':
        return xarray.open_dataset(fn, group=group, autoclose=True)

    tlim = _tlim(tlim)

    info = rinexinfo(fn)
    if int(info['version']) == 2:
        nav = rinexnav2(fn, tlim)
    elif int(info['version']) == 3:
        nav = rinexnav3(fn, tlim)
    else:
        raise ValueError(f'unknown RINEX  {info}  {fn}')

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
             tlim: Tuple[datetime, datetime]=None,
             useindicators: bool=False,
             verbose: bool=False) -> xarray.Dataset:
    """
    Read RINEX 2,3 OBS files in ASCII or GZIP
    """

    fn = Path(fn).expanduser()
# %% NetCDF4
    if fn.suffix == '.nc':
        try:
            logging.debug(f'loading {fn} with xarray')
            return xarray.open_dataset(fn, group=group, autoclose=True)
        except OSError:
            logging.error(f'Group {group} not found in {fn}')
            return

    tlim = _tlim(tlim)
# %% version selection
    info = rinexinfo(fn)

    if int(info['version']) == 2:
        obs = rinexobs2(fn, use, tlim=tlim, useindicators=useindicators, verbose=verbose)
    elif int(info['version']) == 3:
        obs = rinexobs3(fn, use, tlim=tlim, useindicators=useindicators, verbose=verbose)
    else:
        raise ValueError(f'unknown RINEX {info}  {fn}')
# %% optional output write
    if ofn:
        ofn = Path(ofn).expanduser()
        print('saving OBS data to', ofn)
        wmode = 'a' if ofn.is_file() else 'w'

        enc = {k: {'zlib': True, 'complevel': COMPLVL, 'fletcher32': True}
               for k in obs.data_vars}
        obs.to_netcdf(ofn, group=group, mode=wmode, encoding=enc)

    return obs


def gettime(fn: Path) -> xarray.DataArray:
    """
    get times in RINEX 2/3 file
    Note: in header,
        * TIME OF FIRST OBS is mandatory
        * TIME OF LAST OBS is optional
    """
    fn = Path(fn).expanduser()

    info = rinexinfo(fn)
    if rinextype(fn) != 'obs':
        raise ValueError('per-observation time is in OBS files')
# %% select function
    if int(info['version']) == 2:
        times = gettime2(fn)
    elif int(info['version']) == 3:
        times = gettime3(fn)
    else:
        raise ValueError(f'unknown RINEX {info}  {fn}')

    return times


def rinextype(fn: Path) -> str:
    """
    based on file extension only, does not actually inspect the file--that comes later
    """
    if fn.suffix in ('.gz', '.zip', '.Z'):
        fnl = fn.stem.lower()
    else:
        fnl = fn.name.lower()

    if fnl.endswith(('o', 'o.rnx')):
        return 'obs'
    elif fnl.endswith(('e', 'g', 'n', 'n.rnx')):
        return 'nav'
    elif fnl.endswith('.crx'):
        raise NotImplementedError('need to convert Hatanaka compressed RINEX: http://terras.gsi.go.jp/ja/crx2rnx.html')
    elif fn.suffix.endswith('.nc'):
        return 'nc'
    else:
        raise ValueError(f"I dont know what type of file you're trying to read: {fn}")


def rinexheader(fn: Path) -> Dict[str, Any]:
    """
    retrieve RINEX 2/3 header as unparsed dict()
    """
    fn = Path(fn).expanduser()

    info = rinexinfo(fn)
    rtype = rinextype(fn)

    if int(info['version']) == 2:
        if rtype == 'obs':
            hdr = obsheader2(fn)
        elif rtype == 'nav':
            hdr = navheader2(fn)
        else:
            raise ValueError(f'Unknown rinex type in {fn}')
    elif int(info['version']) == 3:
        if rtype == 'obs':
            hdr = obsheader3(fn)
        elif rtype == 'nav':
            hdr = navheader3(fn)
        else:
            raise ValueError(f'Unknown rinex type in {fn}')
    else:
        raise ValueError(f'unknown RINEX {info}  {fn}')

    return hdr


def _tlim(tlim: Optional[Tuple[datetime, datetime]]) -> Optional[Tuple[datetime, datetime]]:
    if tlim is not None and len(tlim) == 2 and isinstance(tlim[0], str):
        tlim = tuple(map(parse, tlim))
    elif tlim is None:
        pass
    else:
        raise ValueError(f'Not sure what time limits are: {tlim}')

    return tlim
