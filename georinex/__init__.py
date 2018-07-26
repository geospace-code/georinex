from pathlib import Path
import logging
import xarray
from typing import Union, Tuple, Dict, Any, Optional
from datetime import datetime
from dateutil.parser import parse
#
from .io import rinexinfo
from .rinex2 import rinexnav2, rinexobs2, obsheader2, navheader2
from .rinex3 import rinexnav3, rinexobs3, obsheader3, navheader3

# for NetCDF compression. too high slows down with little space savings.
COMPLVL = 1


def readrinex(rinexfn: Path, outfn: Path=None,
              use: Union[str, list, tuple]=None,
              tlim: Union[None, Tuple[datetime, datetime]]=None,
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
        nav = rinexnav(rinexfn, outfn)
    elif rtype == 'obs':
        obs = rinexobs(rinexfn, outfn, use=use, tlim=tlim, useindicators=useindicators, verbose=verbose)
    elif rtype == 'nc':
        nav = rinexnav(rinexfn)
        obs = rinexobs(rinexfn)
    else:
        raise ValueError(f"I dont know what type of file you're trying to read: {rinexfn}")

    return obs, nav
# %% Navigation file


def rinexnav(fn: Path, ofn: Path=None, group: str='NAV') -> xarray.Dataset:
    """ Read RINEX 2,3  NAV files in ASCII or GZIP"""
    fn = Path(fn).expanduser()
    if fn.suffix == '.nc':
        try:
            return xarray.open_dataset(fn, group=group, autoclose=True)
        except OSError:
            logging.error(f'Group {group} not found in {fn}')
            return

    info = rinexinfo(fn)
    if int(info['version']) == 2:
        nav = rinexnav2(fn)
    elif int(info['version']) == 3:
        nav = rinexnav3(fn)
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
             tlim: Optional[Tuple[datetime, datetime]]=None,
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
# %% time limits
    if tlim is not None and len(tlim) == 2 and isinstance(tlim[0], str):
        tlim = tuple(map(parse, tlim))
    elif tlim is None:
        pass
    else:
        raise ValueError(f'Not sure what time limits are: {tlim}')
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


def rinextype(fn: Path) -> str:
    if fn.suffix in ('.gz', '.zip'):
        fnl = fn.stem.lower()
    else:
        fnl = fn.name.lower()

    if fnl.endswith('o') or fnl.endswith('o.rnx'):
        return 'obs'
    elif fnl.endswith('n') or fnl.endswith('n.rnx'):
        return 'nav'
    elif fnl.endswith('.crx'):
        raise NotImplementedError('Hatanaka compressed RINEX is not yet supported')
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
