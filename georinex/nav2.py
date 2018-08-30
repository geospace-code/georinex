#!/usr/bin/env python
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Sequence
from typing.io import TextIO
import xarray
import numpy as np
import logging
from .io import opener, rinexinfo
#
STARTCOL2 = 3  # column where numerical data starts for RINEX 2
Nl = {'G': 7, 'R': 3, 'E': 7}   # number of additional SV lines


def rinexnav2(fn: Path,
              tlim: Sequence[datetime]=None) -> xarray.Dataset:
    """
    Reads RINEX 2.x NAV files
    Michael Hirsch, Ph.D.
    SciVision, Inc.

    http://gage14.upc.es/gLAB/HTML/GPS_Navigation_Rinex_v2.11.html
    ftp://igs.org/pub/data/format/rinex211.txt
    """
    fn = Path(fn).expanduser()

    Lf = 19  # string length per field

    svs = []
    times = []
    raws = []

    with opener(fn) as f:

        header = navheader2(f)

        if header['filetype'] == 'N':
            svtype = 'G'
            fields = ['SVclockBias', 'SVclockDrift', 'SVclockDriftRate',
                      'IODE', 'Crs', 'DeltaN', 'M0',
                      'Cuc', 'Eccentricity', 'Cus', 'sqrtA',
                      'Toe', 'Cic', 'Omega0', 'Cis',
                      'Io', 'Crc', 'omega', 'OmegaDot',
                      'IDOT', 'CodesL2', 'GPSWeek', 'L2Pflag',
                      'SVacc', 'health', 'TGD', 'IODC',
                      'TransTime', 'FitIntvl']
        elif header['filetype'] == 'G':
            svtype = 'R'  # GLONASS
            fields = ['SVclockBias', 'SVrelFreqBias', 'MessageFrameTime',
                      'X', 'dX', 'dX2', 'health',
                      'Y', 'dY', 'dY2', 'FreqNum',
                      'Z', 'dZ', 'dZ2', 'AgeOpInfo']
        elif header['filetype'] == 'E':
            svtype = 'E'  # Galileo
            fields = ['SVclockBias', 'SVclockDrift', 'SVclockDriftRate',
                      'IODnav', 'Crs', 'DeltaN', 'M0',
                      'Cuc', 'Eccentricity', 'Cus', 'sqrtA',
                      'Toe', 'Cic', 'Omega0', 'Cis',
                      'Io', 'Crc', 'omega', 'OmegaDot',
                      'IDOT', 'DataSrc', 'GALWeek',
                      'SISA', 'health', 'BGDe5a', 'BGDe5b',
                      'TransTime']
        else:
            raise NotImplementedError(f'I do not yet handle Rinex 2 NAV {header["sys"]}  {fn}')
# %% read data
        for ln in f:
            time = _timenav(ln)

            if tlim is not None:
                if time < tlim[0]:
                    _skip(f, Nl[header['systems']])
                    continue
                elif time > tlim[1]:
                    break
# %% format I2 http://gage.upc.edu/sites/default/files/gLAB/HTML/GPS_Navigation_Rinex_v2.11.html
            svs.append(f'{svtype}{ln[:2]}')

            times.append(time)
            """
            now get the data as one big long string per SV
            """
            raw = ln[22:79]  # NOTE: MUST be 79, not 80 due to some files that put \n a character early!
            for i, ln in zip(range(Nl[header['systems']]), f):
                raw += ln[STARTCOL2:79]
            # one line per SV
            raws.append(raw.replace('D', 'E').replace('\n', ''))
# %% parse
    svs = [s.replace(' ', '0') for s in svs]
    svu = sorted(set(svs))

    atimes = np.asarray(times)
    timesu = np.unique(atimes)
    data = np.empty((len(fields), timesu.size, len(svu)))
    data.fill(np.nan)

    for j, sv in enumerate(svu):  # for each SV, across all values and times...
        svi = [i for i, s in enumerate(svs) if s == sv]  # these rows are for this SV

        tu = np.unique(atimes[svi])  # this SV was seen at these times
        if tu.size != atimes[svi].size:
            logging.warning(f'duplicate times detected, skipping SV {sv}')
            continue

        for i in svi:
            it = np.nonzero(timesu == times[i])[0][0]  # int by defn
            data[:, it, j] = [float(raws[i][k*Lf:(k+1)*Lf]) for k in range(len(fields))]

# %% assemble output
    # NOTE: time must be datetime64[ns] or .to_netcdf will fail
    nav = xarray.Dataset(coords={'time': timesu.astype('datetime64[ns]'), 'sv': svu})

    for i, k in enumerate(fields):
        if k is None:
            continue
        nav[k] = (('time', 'sv'), data[i, :, :])
# %% other attributes
    nav.attrs['version'] = header['version']
    nav.attrs['filename'] = fn.name
    nav.attrs['rinextype'] = 'nav'

    return nav


def navheader2(f: TextIO) -> Dict[str, Any]:
    if isinstance(f, Path):
        fn = f
        with fn.open('r') as f:
            return navheader2(f)

# %%verify RINEX version, and that it's NAV
    hdr = rinexinfo(f)
    if int(hdr['version']) != 2:
        raise ValueError('see rinexnav3() for RINEX 3.0 files')

    for ln in f:
        if 'END OF HEADER' in ln:
            break

        hdr[ln[60:]] = ln[:60]

    return hdr


def _timenav(ln: str) -> datetime:
    """
    Python >= 3.7 supports nanoseconds.  https://www.python.org/dev/peps/pep-0564/
    Python < 3.7 supports microseconds.
    """
    year = int(ln[3:5])
    if 80 <= year <= 99:
        year += 1900
    elif year < 80:  # because we might pass in four-digit year
        year += 2000
    else:
        raise ValueError(f'unknown year format {year}')

    return datetime(year=year,
                    month=int(ln[6:8]),
                    day=int(ln[9:11]),
                    hour=int(ln[12:14]),
                    minute=int(ln[15:17]),
                    second=int(float(ln[17:20])),
                    microsecond=int(float(ln[17:22]) % 1 * 1000000)
                    )


def _skip(f: TextIO, Nl: int):
    for _, _ in zip(range(Nl), f):
        pass


def navtime2(fn: Path) -> xarray.DataArray:
    """
    read all times in RINEX 2 NAV file
    """
    times = []
    with opener(fn) as f:
        hdr = navheader2(f)

        while True:
            ln = f.readline()
            if not ln:
                break

            times.append(_timenav(ln))

            _skip(f, Nl[hdr['systems']])

    times = np.unique(times)

    timedat = xarray.DataArray(times,
                               dims=['time'],
                               attrs={'filename': fn,
                                      'interval': ''})

    return timedat
