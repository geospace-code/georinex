from .io import opener
from pathlib import Path
import numpy as np
import logging
from datetime import datetime
from io import BytesIO
import xarray
from typing import Union, Dict, List, Tuple, Any, Optional
from typing.io import TextIO
#
"""https://github.com/mvglasow/satstat/wiki/NMEA-IDs"""
SBAS = 100  # offset for ID
GLONASS = 37
QZSS = 192
BEIDOU = 0


def rinexobs3(fn: Path, use: Any,
              tlim: Optional[Tuple[datetime, datetime]],
              useindicators: bool,
              verbose: bool=False) -> xarray.Dataset:
    """
    process RINEX 3 OBS data
    """

    if (not use or not use[0].strip() or
        isinstance(use, str) and use.lower() in ('m', 'all') or
            isinstance(use, (tuple, list, np.ndarray)) and use[0].lower() in ('m', 'all')):

        use = None
# %% allocate
    # times = gettime3(fn)
    data: xarray.Dataset = None  # data = xarray.Dataset(coords={'time': times, 'sv': None})
    if tlim is not None:
        assert isinstance(tlim[0], datetime), 'time bounds are specified as datetime.datetime'
# %% loop
    with opener(fn) as f:
        version = float(f.readline()[:9])  # yes :9
        header = obsheader3(f, use)
# %% process OBS file
        for ln in f:
            if not ln.startswith('>'):  # end of file
                break

            try:
                time = _timeobs(ln, fn)
            except ValueError:  # garbage between header and RINEX data
                logging.error(f'garbage detected in {fn}, trying to parse at next time step')
                continue
# %% get SV indices
            # Number of visible satellites this time %i3  pg. A13
            Nsv = int(ln[33:35])

            sv = []
            raw = ''
            for i, ln in zip(range(Nsv), f):
                k = ln[:3]
                sv.append(k)
                raw += ln[3:]

            if tlim is not None:
                if time < tlim[0]:
                    continue
                elif time > tlim[1]:
                    break

            if verbose:
                print(time, end="\r")

            data = _eachtime(data, raw, header, time, sv, useindicators, verbose)

    data.attrs['filename'] = fn.name
    data.attrs['version'] = version
    data.attrs['position'] = header['position']
    # data.attrs['toffset'] = toffset

    return data


def _timeobs(ln: str, fn: Path) -> datetime:

    if not ln.startswith('>'):  # pg. A13
        raise ValueError(f'RINEX 3 line beginning > is not present in {fn}')
    """
    Python >=merge 3.7 supports nanoseconds.  https://www.python.org/dev/peps/pep-0564/
    Python < 3.7 supports microseconds.
    """
    return datetime(int(ln[2:6]), int(ln[7:9]), int(ln[10:12]),
                    hour=int(ln[13:15]), minute=int(ln[16:18]),
                    second=int(ln[19:21]),
                    microsecond=int(float(ln[19:29]) % 1 * 1000000))


def gettime3(fn: Path) -> xarray.DataArray:
    """
    return all times in RINEX file
    """
    times = []
    header = obsheader3(fn)

    with opener(fn) as f:
        for ln in f:
            if ln.startswith('>'):
                times.append(_timeobs(ln, fn))

    timedat = xarray.DataArray(times,
                               dims=['time'],
                               attrs={'filename': fn,
                                      'interval': header['interval']})

    return timedat


def _eachtime(data: xarray.Dataset, raw: str, header: dict, time: datetime, sv: List[str],
              useindicators: bool, verbose: bool) -> xarray.Dataset:
    darr = np.atleast_2d(np.genfromtxt(BytesIO(raw.encode('ascii')),
                                       delimiter=(14, 1, 1)*header['Fmax']))
# %% assign data for each time step
    for sk in header['fields']:  # for each satellite system type (G,R,S, etc.)
        si = [i for i, s in enumerate(sv) if s[0] in sk]
        if len(si) == 0:  # no SV of this system "sk" at this time
            continue

        garr = darr[si, :]
        gsv = np.array(sv)[si]

        dsf: Dict[str, tuple] = {}
        for i, k in enumerate(header['fields'][sk]):
            dsf[k] = (('time', 'sv'), np.atleast_2d(garr[:, i*3]))

            if useindicators:
                dsf = _indicators(dsf, k, garr[:, i*3+1:i*3+3])

        if verbose:
            print(time, '\r', end='')

        if data is None:
            # , attrs={'toffset':toffset})
            data = xarray.Dataset(
                dsf, coords={'time': [time], 'sv': gsv})
        else:
            if len(header['fields']) == 1:
                data = xarray.concat((data,
                                      xarray.Dataset(dsf, coords={'time': [time], 'sv': gsv})),
                                     dim='time')
            else:  # general case, slower for different satellite systems all together
                data = xarray.merge((data,
                                     xarray.Dataset(dsf, coords={'time': [time], 'sv': gsv})))

    return data


def _indicators(d: dict, k: str, arr: np.ndarray) -> Dict[str, tuple]:
    if k.startswith(('L1', 'L2')):
        d[k+'lli'] = (('time', 'sv'), np.atleast_2d(arr[:, 0]))

    d[k+'ssi'] = (('time', 'sv'), np.atleast_2d(arr[:, 1]))

    return d


def obsheader3(f: TextIO, use: Union[str, list, tuple]= None) -> Dict[str, Any]:
    """ get RINEX 3 OBS types, for each system type"""
    header: Dict[str, Any] = {}
    fields = {}
    Fmax = 0

    if isinstance(f, Path):
        fn = f
        with opener(fn) as f:
            return obsheader3(f)
    # Capture header info
    for ln in f:
        if "END OF HEADER" in ln:
            break

        h = ln[60:80]
        c = ln[:60]
        if 'SYS / # / OBS TYPES' in h:
            k = c[0]
            fields[k] = c[6:60].split()
            N = int(c[3:6])
            Fmax = max(N, Fmax)

            n = N-13
            while n > 0:  # Rinex 3.03, pg. A6, A7
                ln = f.readline()
                assert 'SYS / # / OBS TYPES' in ln[60:]
                fields[k] += ln[6:60].split()
                n -= 13

            assert len(fields[k]) == N

            continue

        if h.strip() not in header:  # Header label
            header[h.strip()] = c  # don't strip for fixed-width parsers
            # string with info
        else:  # concatenate to the existing string
            header[h.strip()] += " " + c
# %% useful values

    # list with x,y,z cartesian
    header['position'] = [float(j) for j in header['APPROX POSITION XYZ'].split()]
# %% time
    t0s = header['TIME OF FIRST OBS']
    # NOTE: must do second=int(float()) due to non-conforming files
    header['t0'] = datetime(year=int(t0s[:6]), month=int(t0s[6:12]), day=int(t0s[12:18]),
                            hour=int(t0s[18:24]), minute=int(t0s[24:30]), second=int(float(t0s[30:36])),
                            microsecond=int(float(t0s[30:43]) % 1 * 1000000))

    try:
        header['interval'] = float(header['INTERVAL'][:10])
    except KeyError:
        header['interval'] = None
# %% select specific satellite systems only (optional)
    if use is not None:
        fields = {k: fields[k] for k in use}

    header['fields'] = fields
    header['Fmax'] = Fmax

    return header
