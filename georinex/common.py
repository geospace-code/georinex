from pathlib import Path
from datetime import timedelta
from typing import Dict, Any
import numpy as np
import logging
try:
    import psutil
except ImportError:
    psutil = None


def check_unique_times(times: np.ndarray) -> bool:
    Nuniq = np.unique(times).size
    Ntimes = times.size

    ok = Ntimes == Nuniq

    if not ok:
        logging.error(f'only {Nuniq} times out of {Ntimes} are unique times')

    return ok


def rinex_string_to_float(s: str) -> float:
    return float(s.replace('D', 'E'))


def check_ram(memneed: int, fn: Path):
    if psutil is None:
        return

    mem = psutil.virtual_memory()

    if memneed > 0.5*mem.available:  # because of array copy Numpy => Xarray
        raise RuntimeError(f'{fn} needs {memneed/1e9} GBytes RAM, but only {mem.available/1e9} Gbytes available \n'
                           'try fast=False to reduce RAM usage, raise a GitHub Issue to let us help')


def determine_time_system(header: Dict[str, Any]) -> str:
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
        ts = header['TIME OF FIRST OBS'][48:51].strip()
    else:
        raise ValueError(f'unknown file type {file_type}')

    return ts


def _check_time_interval(interval: Any) -> timedelta:
    if isinstance(interval, (float, int)):
        if interval < 0:
            raise ValueError('time interval must be non-negative')
        interval = timedelta(seconds=interval)
    elif isinstance(interval, timedelta):
        pass
    elif interval is None:
        pass
    else:
        raise TypeError('expect time interval in seconds (float,int) or datetime.timedelta')

    return interval
