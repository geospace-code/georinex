from pathlib import Path
import xarray
from typing import Union, Tuple, Dict, Sequence
from typing.io import TextIO
from datetime import datetime, timedelta
import logging

from .io import rinexinfo
from .obs2 import rinexobs2
from .obs3 import rinexobs3
from .nav2 import rinexnav2
from .nav3 import rinexnav3
from .utils import _tlim

# for NetCDF compression. too high slows down with little space savings.
ENC = {'zlib': True, 'complevel': 1, 'fletcher32': True}


def load(rinexfn: Union[TextIO, str, Path],
         out: Path = None,
         use: Sequence[str] = None,
         tlim: Tuple[datetime, datetime] = None,
         useindicators: bool = False,
         meas: Sequence[str] = None,
         verbose: bool = False,
         *,
         fast: bool = True,
         interval: Union[float, int, timedelta] = None) -> Union[xarray.Dataset, Dict[str, xarray.Dataset]]:
    """
    Reads OBS, NAV in RINEX 2.x and 3.x

    Files / StringIO input may be plain ASCII text or compressed (including Hatanaka)
    """
    if verbose:
        logging.basicConfig(level=logging.INFO)

    if isinstance(rinexfn, (str, Path)):
        rinexfn = Path(rinexfn).expanduser()
# %% determine if/where to write NetCDF4/HDF5 output
    outfn = None
    if out:
        out = Path(out).expanduser()
        if out.is_dir():
            outfn = out / (rinexfn.name + '.nc')  # not with_suffix to keep unique RINEX 2 filenames
        elif out.suffix == '.nc':
            outfn = out
        else:
            raise ValueError(f'not sure what output is wanted: {out}')
# %% main program
    if tlim is not None:
        if len(tlim) != 2:
            raise ValueError('time bounds are specified as start stop')
        if tlim[1] < tlim[0]:
            raise ValueError('stop time must be after start time')

    info = rinexinfo(rinexfn)

    if info['rinextype'] == 'nav':
        return rinexnav(rinexfn, outfn, use=use, tlim=tlim)
    elif info['rinextype'] == 'obs':
        return rinexobs(rinexfn, outfn, use=use, tlim=tlim,
                        useindicators=useindicators, meas=meas,
                        verbose=verbose, fast=fast, interval=interval)
    elif rinexfn.suffix == '.nc':
        # outfn not used here, because we already have the converted file!
        try:
            nav = rinexnav(rinexfn)
        except LookupError:
            nav = None

        try:
            obs = rinexobs(rinexfn)
        except LookupError:
            obs = None

        if nav is not None and obs is not None:
            return {'nav': nav, 'obs': rinexobs(rinexfn)}
        elif nav is not None:
            return nav
        elif obs is not None:
            return obs
        else:
            raise ValueError(f'No data of known format found in {rinexfn}')
    else:
        raise ValueError(f"What kind of RINEX file is: {rinexfn}")


def batch_convert(path: Path, glob: str, out: Path,
                  use: Sequence[str] = None,
                  tlim: Tuple[datetime, datetime] = None,
                  useindicators: bool = False,
                  meas: Sequence[str] = None,
                  verbose: bool = False,
                  *,
                  fast: bool = True):

    path = Path(path).expanduser()

    flist = (f for f in path.glob(glob) if f.is_file())

    for fn in flist:
        try:
            load(fn, out, use=use, tlim=tlim,
                 useindicators=useindicators, meas=meas,
                 verbose=verbose, fast=fast)
        except Exception as e:
            logging.error(f'{fn.name}: {e}')


def rinexnav(fn: Union[TextIO, str, Path],
             outfn: Path = None,
             use: Sequence[str] = None,
             group: str = 'NAV',
             tlim: Tuple[datetime, datetime] = None) -> xarray.Dataset:
    """ Read RINEX 2 or 3  NAV files"""

    if isinstance(fn, (str, Path)):
        fn = Path(fn).expanduser()

        if fn.suffix == '.nc':
            try:
                return xarray.open_dataset(fn, group=group)
            except OSError as e:
                raise LookupError(f'Group {group} not found in {fn}    {e}')

    tlim = _tlim(tlim)

    info = rinexinfo(fn)
    if int(info['version']) == 2:
        nav = rinexnav2(fn, tlim=tlim)
    elif int(info['version']) == 3:
        nav = rinexnav3(fn, use=use, tlim=tlim)
    else:
        raise LookupError(f'unknown RINEX  {info}  {fn}')

# %% optional output write
    if outfn:
        outfn = Path(outfn).expanduser()
        wmode = _groupexists(outfn, group)

        enc = {k: ENC for k in nav.data_vars}
        nav.to_netcdf(outfn, group=group, mode=wmode, encoding=enc)

    return nav

# %% Observation File


def rinexobs(fn: Union[TextIO, str, Path],
             outfn: Path = None,
             use: Sequence[str] = None,
             group: str = 'OBS',
             tlim: Tuple[datetime, datetime] = None,
             useindicators: bool = False,
             meas: Sequence[str] = None,
             verbose: bool = False,
             *,
             fast: bool = True,
             interval: Union[float, int, timedelta] = None) -> xarray.Dataset:
    """
    Read RINEX 2.x and 3.x OBS files in ASCII or GZIP (or Hatanaka)
    """

    if isinstance(fn, (str, Path)):
        fn = Path(fn).expanduser()
# %% NetCDF4
        if fn.suffix == '.nc':
            try:
                return xarray.open_dataset(fn, group=group)
            except OSError as e:
                raise LookupError(f'Group {group} not found in {fn}   {e}')

    tlim = _tlim(tlim)
# %% version selection
    info = rinexinfo(fn)

    if int(info['version']) in (1, 2):
        obs = rinexobs2(fn, use, tlim=tlim,
                        useindicators=useindicators, meas=meas,
                        verbose=verbose,
                        fast=fast, interval=interval)
    elif int(info['version']) == 3:
        obs = rinexobs3(fn, use, tlim=tlim,
                        useindicators=useindicators, meas=meas,
                        verbose=verbose,
                        fast=fast, interval=interval)
    else:
        raise ValueError(f'unknown RINEX {info}  {fn}')

# %% optional output write
    if outfn:
        outfn = Path(outfn).expanduser()
        wmode = _groupexists(outfn, group)

        enc = {k: ENC for k in obs.data_vars}
        obs.to_netcdf(outfn, group=group, mode=wmode, encoding=enc)

    return obs


def _groupexists(fn: Path, group: str) -> str:
    print(f'saving {group}:', fn)
    if not fn.is_file():
        return 'w'

    # be sure there isn't already NAV in it
    try:
        xarray.open_dataset(fn, group=group)
        raise ValueError(f'{group} already in {fn}')
    except OSError:
        pass

    return 'a'
