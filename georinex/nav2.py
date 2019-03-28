#!/usr/bin/env python
from pathlib import Path
from datetime import datetime
from typing import Dict, Union, Any, Sequence
from typing.io import TextIO
import xarray
import numpy as np
import logging

from .io import opener, rinexinfo
from .common import rinex_string_to_float
#
STARTCOL2 = 3  # column where numerical data starts for RINEX 2
Nl = {'G': 7, 'R': 3, 'E': 7}   # number of additional SV lines


def rinexnav2(fn: Union[TextIO, str, Path],
              tlim: Sequence[datetime] = None) -> xarray.Dataset:
    """
    Reads RINEX 2.x NAV files
    Michael Hirsch, Ph.D.
    SciVision, Inc.

    http://gage14.upc.es/gLAB/HTML/GPS_Navigation_Rinex_v2.11.html
    ftp://igs.org/pub/data/format/rinex211.txt
    """
    if isinstance(fn, (str, Path)):
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
            try:
                time = _timenav(ln)
            except ValueError:
                continue

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
            # NOTE: Sebastijan added .replace('  ', ' ').replace(' -', '-')
            # here, I would like to see a file that needs this first, to be sure
            # I'm not needlessly slowing down reading or creating new problems.
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
            """
            some files sometimes drop the last measurement, this fixes that.
            It assumes the blank is always in the last measurement for now.
            """
            dvec = [float(raws[i][k*Lf:(k+1)*Lf]) for k in range(min(len(fields), len(raws[i])//Lf))]
            data[:len(dvec), it, j] = dvec

# %% assemble output
    # NOTE: time must be datetime64[ns] or .to_netcdf will fail
    nav = xarray.Dataset(coords={'time': timesu.astype('datetime64[ns]'), 'sv': svu})

    for i, k in enumerate(fields):
        if k is None:
            continue
        nav[k] = (('time', 'sv'), data[i, :, :])

    # GLONASS uses kilometers to report its ephemeris.
    # Convert to meters here to be consistent with NAV3 implementation.
    if svtype == 'R':
        for name in ['X', 'Y', 'Z', 'dX', 'dY', 'dZ', 'dX2', 'dY2', 'dZ2']:
            nav[name] *= 1e3

# %% other attributes
    nav.attrs['version'] = header['version']
    nav.attrs['svtype'] = [svtype]  # Use list for consistency with NAV3.
    nav.attrs['rinextype'] = 'nav'
    if isinstance(fn, Path):
        nav.attrs['filename'] = fn.name

    if 'ION ALPHA' in header and 'ION BETA' in header:
        alpha = header['ION ALPHA']
        alpha = [rinex_string_to_float(alpha[2 + i*12:2 + (i+1)*12])
                 for i in range(4)]
        beta = header['ION BETA']
        beta = [rinex_string_to_float(beta[2 + i*12:2 + (i+1)*12])
                for i in range(4)]
        nav.attrs['ionospheric_corr_GPS'] = np.hstack((alpha, beta))

    return nav


def navheader2(f: TextIO) -> Dict[str, Any]:
    """
    For RINEX NAV version 2 only. End users should use rinexheader()
    """
    if isinstance(f, (str, Path)):
        with opener(f, header=True) as h:
            return navheader2(h)

    hdr = rinexinfo(f)

    for ln in f:
        if 'END OF HEADER' in ln:
            break
        kind, content = ln[60:].strip(), ln[:60]
        hdr[kind] = content

    return hdr


def _timenav(ln: str) -> datetime:

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


def navtime2(fn: Union[TextIO, Path]) -> np.ndarray:
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

            try:
                time = _timenav(ln)
            except ValueError:
                continue

            times.append(time)

            _skip(f, Nl[hdr['systems']])

    return np.unique(times)
