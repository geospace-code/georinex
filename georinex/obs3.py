import io
import logging
from itertools import chain
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Union, List, Tuple, Any, Sequence
from typing.io import TextIO

import xarray
import numpy as np

from .io import opener

try:
    from pymap3d import ecef2geodetic
except ImportError:
    ecef2geodetic = None
#
from .common import determine_time_system, _check_time_interval
from .io import rinexinfo
"""https://github.com/mvglasow/satstat/wiki/NMEA-IDs"""

SBAS = 100  # offset for ID
GLONASS = 37
QZSS = 192
BEIDOU = 0


def rinexobs3(fn: Union[TextIO, str, Path],
              use: Sequence[str] = None,
              tlim: Tuple[datetime, datetime] = None,
              useindicators: bool = False,
              meas: Sequence[str] = None,
              verbose: bool = False,
              *,
              fast: bool = False,
              interval: Union[float, int, timedelta] = None) -> xarray.Dataset:
    """
    process RINEX 3 OBS data

    fn: RINEX OBS 3 filename
    use: 'G'  or ['G', 'R'] or similar

    tlim: read between these time bounds
    useindicators: SSI, LLI are output
    meas:  'L1C'  or  ['L1C', 'C1C'] or similar

    fast:
          TODO: FUTURE, not yet enabled for OBS3
          speculative preallocation based on minimum SV assumption and file size.
          Avoids double-reading file and more complicated linked lists.
          Believed that Numpy array should be faster than lists anyway.
          Reduce Nsvmin if error (let us know)

    interval: allows decimating file read by time e.g. every 5 seconds.
                Useful to speed up reading of very large RINEX files
    """

    interval = _check_time_interval(interval)

    if isinstance(use, str):
        use = [use]

    if isinstance(meas, str):
        meas = [meas]

    if not use or not use[0].strip():
        use = None

    if not meas or not meas[0].strip():
        meas = None
# %% allocate
    # times = obstime3(fn)
    data = xarray.Dataset({}, coords={'time': [], 'sv': []})
    if tlim is not None and not isinstance(tlim[0], datetime):
        raise TypeError('time bounds are not specified as datetime.datetime')

    last_epoch = None
# %% loop
    with opener(fn) as f:
        hdr = obsheader3(f, use, meas)
# %% process OBS file
        for ln in f:
            if not ln.startswith('>'):  # end of file
                break

            try:
                time, in_range = _timeobs(ln, tlim, last_epoch, interval)
            except ValueError:  # garbage between header and RINEX data
                logging.debug(f'garbage detected in {fn}, trying to parse at next time step')
                continue

            # Number of visible satellites this time %i3  pg. A13
            Nsv = int(ln[33:35])
            if in_range == -1:
                for _ in range(Nsv):
                    next(f)
                continue

            if in_range == 1:
                break

            last_epoch = time

            sv = []
            raw = ''
            for i, ln in zip(range(Nsv), f):
                sv.append(ln[:3])
                raw += ln[3:]

            if verbose:
                print(time, end="\r")

            data = _epoch(data, raw, hdr, time, sv, useindicators, verbose)
# %% patch SV names in case of "G 7" => "G07"
    data = data.assign_coords(sv=[s.replace(' ', '0') for s in data.sv.values.tolist()])
# %% other attributes
    data.attrs['version'] = hdr['version']
    data.attrs['rinextype'] = 'obs'
    data.attrs['fast_processing'] = 0  # bool is not allowed in NetCDF4
    data.attrs['time_system'] = determine_time_system(hdr)
    if isinstance(fn, Path):
        data.attrs['filename'] = fn.name

    try:
        data.attrs['position'] = hdr['position']
        if ecef2geodetic is not None:
            data.attrs['position_geodetic'] = hdr['position_geodetic']
    except KeyError:
        pass

    # data.attrs['toffset'] = toffset

    return data


def _timeobs(ln: str, tlim: Tuple[datetime, datetime], last_epoch: datetime, interval: timedelta) -> Tuple[datetime, int]:
    """
    convert time from RINEX 3 OBS text to datetime
    """

    curr_time = datetime(int(ln[2:6]), int(ln[7:9]), int(ln[10:12]),
                         hour=int(ln[13:15]), minute=int(ln[16:18]),
                         second=int(ln[19:21]),
                         microsecond=int(float(ln[19:29]) % 1 * 1000000))

    in_range = 0
    if tlim is not None:
        if curr_time < tlim[0]:
            in_range = -1
        if curr_time > tlim[1]:
            in_range = 1

    if interval is not None and last_epoch is not None and in_range == 0:
        in_range = -1 if (curr_time - last_epoch < interval) else 0

    return (curr_time, in_range)

def obstime3(fn: Union[TextIO, Path],
             verbose: bool = False) -> np.ndarray:
    """
    return all times in RINEX file
    """
    times = []

    with opener(fn) as f:
        for ln in f:
            if ln.startswith('>'):
                times.append(_timeobs(ln))

    return np.asarray(times)


def _epoch(data: xarray.Dataset, raw: str,
           hdr: Dict[str, Any],
           time: datetime,
           sv: List[str],
           useindicators: bool,
           verbose: bool) -> xarray.Dataset:
    """
    block processing of each epoch (time step)
    """
    darr = np.atleast_2d(np.genfromtxt(io.BytesIO(raw.encode('ascii')),
                                       delimiter=(14, 1, 1) * hdr['Fmax']))
# %% assign data for each time step
    for sk in hdr['fields']:  # for each satellite system type (G,R,S, etc.)
        # satellite indices "si" to extract from this time's measurements
        si = [i for i, s in enumerate(sv) if s[0] in sk]
        if len(si) == 0:  # no SV of this system "sk" at this time
            continue

        # measurement indices "di" to extract at this time step
        di = hdr['fields_ind'][sk]
        garr = darr[si, :]
        garr = garr[:, di]

        gsv = np.array(sv)[si]

        dsf: Dict[str, tuple] = {}
        for i, k in enumerate(hdr['fields'][sk]):
            dsf[k] = (('time', 'sv'), np.atleast_2d(garr[:, i*3]))

            if useindicators:
                dsf = _indicators(dsf, k, garr[:, i*3+1:i*3+3])

        if verbose:
            print(time, '\r', end='')

        epoch_data = xarray.Dataset(dsf, coords={'time': [time], 'sv': gsv})
        if len(data) == 0:
            data = epoch_data
        elif len(hdr['fields']) == 1:  # one satellite system selected, faster to process
            data = xarray.concat((data, epoch_data), dim='time')
        else:  # general case, slower for different satellite systems all together
            data = xarray.merge((data, epoch_data))

    return data


def _indicators(d: dict, k: str, arr: np.ndarray) -> Dict[str, tuple]:
    """
    handle LLI (loss of lock) and SSI (signal strength)
    """
    if k.startswith(('L1', 'L2')):
        d[k+'lli'] = (('time', 'sv'), np.atleast_2d(arr[:, 0]))

    d[k+'ssi'] = (('time', 'sv'), np.atleast_2d(arr[:, 1]))

    return d


def obsheader3(f: TextIO,
               use: Sequence[str] = None,
               meas: Sequence[str] = None) -> Dict[str, Any]:
    """
    get RINEX 3 OBS types, for each system type
    optionally, select system type and/or measurement type to greatly
    speed reading and save memory (RAM, disk)
    """
    # if isinstance(f, (str, Path)):
    #     with opener(f, header=True) as h:
    #         return obsheader3(h, use, meas)

    hdr = {}
    hdr['attr'] = rinexinfo(f)
    hdr['meas'] = {}
    fields = {}

    for ln in f:
        if "END OF HEADER" in ln:
            break

        c, h = ln[:60], ln[60:80]

        if 'MARKER NAME' in h:
            hdr['attr']['name'] = c.strip()
            continue

        satsys = ''
        if 'SYS / # / OBS TYPES' in h:
            satsys = c[0]
            fields[satsys] = c[6:60].split()
            cnt = n = int(c[3:6])
            while n-13 > 0:  # Rinex 3.03, pg. A6, A7
                ln = f.readline()
                assert 'SYS / # / OBS TYPES' in ln[60:80]
                fields[satsys] += ln[6:60].split()
                n -= 13

            assert len(fields[satsys]) == cnt
            continue

        if 'APPROX POSITION XYZ' in h:
            hdr['attr']['pos'] = np.array([float(v) for v in c.split()])
            if ecef2geodetic is not None:
                hdr['attr']['pos_geo'] = ecef2geodetic(*hdr['attr']['pos'])
            continue

        if 'TIME OF FIRST OBS' in h:
            hdr['attr']['time_system'] = c[48:51].strip()
            hdr['attr']['t0'] = datetime(
                year=int(c[:6]), month=int(c[6:12]), day=int(c[12:18]),
                hour=int(c[18:24]), minute=int(c[24:30]),
                second=int(float(c[30:36])),
                microsecond=int(float(c[30:43]) % 1 * 1000000))
            continue

        if 'INTERVAL' in h:
            hdr['attr']['interval'] = float(c[:10])
            continue

# %% select specific satellite systems only (optional)
    set_sys = set(fields.keys())
    set_meas = set(chain.from_iterable(fields.values()))
    if use is not None:
        set_use = set(use)
        if set_use - set_sys:
            raise KeyError(f'system type {use} not found in RINEX file')

        set_sys -= set_use
        for sys in set_sys:
            del fields[sys]
        set_sys = set_use

    if meas is not None:
        set_usemeas = set(meas)
        if set_usemeas - set_meas:
            raise KeyError(f'measurement type {meas} not found in RINEX file')

        for sys in set_sys:
            fields[sys] = list(set_usemeas.intersection(fields[sys]))
            if not fields[sys]:
                del fields[sys]

    # Note: Make a test case for correct filtering of (use, meas)

    if not fields:
        raise ValueError('required system(s)/measurement(s) not present')

    for sys in fields:
        for meas in fields[sys]:
            hdr['meas'][sys + '-' + meas] = {
                'len': None, 'idx': None,
                'data': {'time': None, 'sv': None, 'val': None}
            }

    # TBD add indicator
    return hdr
