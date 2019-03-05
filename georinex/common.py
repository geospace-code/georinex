from pathlib import Path
from datetime import datetime, timedelta
import xarray
from typing import Tuple, Union, Optional
try:
    import psutil
except ImportError:
    psutil = None


def rinex_version(s: str) -> Tuple[float, bool]:
    """

    input: first line of RINEX/CRINEX file

    output: version, is_CRINEX
    """
    if not isinstance(s, str):
        raise TypeError('need first line of RINEX file as string')

    if len(s) >= 80:
        if s[60:80] not in ('RINEX VERSION / TYPE', 'CRINEX VERS   / TYPE'):
            raise ValueError('The first line of the RINEX file header is corrupted.')

    vers = float(s[:9])  # %9.2f
    is_crinex = s[20:40] == 'COMPACT RINEX FORMAT'

    return vers, is_crinex


def rinex_string_to_float(x: str) -> float:
    return float(x.replace('D', 'E'))


def check_ram(memneed: int, fn: Path):
    if psutil is None:
        return

    mem = psutil.virtual_memory()

    if memneed > 0.5*mem.available:  # because of array copy Numpy => Xarray
        raise RuntimeError(f'{fn} needs {memneed/1e9} GBytes RAM, but only {mem.available/1e9} Gbytes available \n'
                           'try fast=False to reduce RAM usage, raise a GitHub Issue to let us help')


def determine_time_system(header: dict) -> str:
    """Determine which time system is used in an observation file."""
    # Current implementation is quite inconsistent in terms what is put into
    # header.
    try:
        file_type = header['RINEX VERSION / TYPE'][40]
    except KeyError:
        file_type = header['systems']

    if file_type == 'G':
        ts = 'GPS'
    elif file_type == 'R':
        ts = 'GLO'
    elif file_type == 'E':
        ts = 'GAL'
    elif file_type == 'J':
        ts = 'QZS'
    elif file_type == 'C':
        ts = 'BDT'
    elif file_type == 'I':
        ts = 'IRN'
    elif file_type == 'M':
        # Else the type is mixed and the time system must be specified in
        # TIME OF FIRST OBS row.
        ts = header['TIME OF FIRST OBS'][48:51]
    else:
        raise ValueError(f'unknown file type {file_type}')

    return ts


def to_datetime(times: xarray.DataArray) -> datetime:
    if not isinstance(times, xarray.DataArray):
        return times

    t = times.values.astype('datetime64[us]').astype(datetime)

    if not isinstance(t, datetime):
        t = t.squeeze()[()]  # might still be array, but squeezed at least

    return t


def _check_time_interval(interval: Union[float, int, timedelta, None]) -> Optional[timedelta]:
    if interval is not None:
        if isinstance(interval, (float, int)):
            if interval < 0:
                raise ValueError('time interval must be non-negative')
            interval = timedelta(seconds=interval)
        elif isinstance(interval, timedelta):
            pass
        else:
            raise TypeError('expect time interval in seconds (float,int) or datetime.timedelta')

    return interval
