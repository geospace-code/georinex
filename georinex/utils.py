from pathlib import Path
from typing import Tuple, Dict, Any, Optional, Sequence, List
from datetime import datetime
from dateutil.parser import parse
import xarray
import pandas
from .io import rinexinfo
from .obs2 import obstime2, obsheader2
from .obs3 import obstime3, obsheader3
from .nav2 import navtime2, navheader2
from .nav3 import navtime3, navheader3


def globber(path: Path, glob: Sequence[str]) -> List[Path]:

    if isinstance(glob, str):
        glob = [glob]

    flist: List[Path] = []
    for g in glob:
        flist += [f for f in path.glob(g) if f.is_file()]

    return flist


def gettime(fn: Path) -> xarray.DataArray:
    """
    get times in RINEX 2/3 file
    Note: in header,
        * TIME OF FIRST OBS is mandatory
        * TIME OF LAST OBS is optional
    """
    fn = Path(fn).expanduser()

    info = rinexinfo(fn)
    assert int(info['version']) in (2, 3)

    rtype = rinextype(fn)

    if rtype not in ('nav', 'obs'):
        raise NotImplementedError('per-observation time is in NAV, OBS files')
# %% select function
    if rtype == 'obs':
        if int(info['version']) == 2:
            times = obstime2(fn)
        elif int(info['version']) == 3:
            times = obstime3(fn)
    elif rtype == 'nav':
        if int(info['version']) == 2:
            times = navtime2(fn)
        elif int(info['version']) == 3:
            times = navtime3(fn)
    else:
        raise ValueError(f'unknown RINEX {info}  {fn}')

    return times


def getlocations(flist: Sequence[Path]) -> pandas.DataFrame:
    """
    retrieve locations of GNSS receivers

    Requires pymap3d.ecef2geodetic
    """
    if isinstance(flist, Path):
        flist = [flist]

    locs = pandas.DataFrame(index=[f.name for f in flist],
                            columns=['lat', 'lon', 'interval'])

    for f in flist:
        try:
            hdr = rinexheader(f)
        except ValueError:
            continue

        if 'position_geodetic' not in hdr:
            continue

        locs.loc[f.name, 'lat'] = hdr['position_geodetic'][0]
        locs.loc[f.name, 'lon'] = hdr['position_geodetic'][1]
        if 'interval' in hdr and hdr['interval'] is not None:
            locs.loc[f.name, 'interval'] = hdr['interval']

    locs = locs.loc[locs.loc[:, ['lat', 'lon']].notna().all(axis=1), :]

    return locs


def rinextype(fn: Path) -> str:
    """
    based on file extension only, does not actually inspect the file--that comes later
    """
    if fn.suffix in ('.gz', '.zip', '.Z'):
        fnl = fn.stem.lower()
    else:
        fnl = fn.name.lower()

    if fnl.endswith(('o', 'o.rnx', 'o.crx')):
        return 'obs'
    elif fnl.endswith(('e', 'g', 'n', 'n.rnx')):
        return 'nav'
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


def _tlim(tlim: Tuple[datetime, datetime]=None) -> Optional[Tuple[datetime, datetime]]:
    if tlim is None:
        pass
    elif len(tlim) == 2 and isinstance(tlim[0], datetime):
        pass
    elif len(tlim) == 2 and isinstance(tlim[0], str):
        tlim = tuple(map(parse, tlim))
    else:
        raise ValueError(f'Not sure what time limits are: {tlim}')

    return tlim
