#!/usr/bin/env python
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Tuple
from typing.io import TextIO
import xarray
import numpy as np
import logging
from io import BytesIO
from .io import opener, rinexinfo
#
STARTCOL2 = 3  # column where numerical data starts for RINEX 2


def rinexnav2(fn: Path, tlim: Tuple[datetime, datetime]=None) -> xarray.Dataset:
    """
    Reads RINEX 2.11 NAV files
    Michael Hirsch, Ph.D.
    SciVision, Inc.

    http://gage14.upc.es/gLAB/HTML/GPS_Navigation_Rinex_v2.11.html
    ftp://igs.org/pub/data/format/rinex211.txt
    """
    fn = Path(fn).expanduser()

    Lf = 19  # string length per field

    svs = []
    times: List[datetime] = []
    raws = []

    with opener(fn) as f:

        header = navheader2(f)

        if header['filetype'] == 'N':
            svtype = 'G'
            Nl = 7  # number of additional lines per record, for RINEX 2 NAV
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
            Nl = 7
            fields = ['SVclockBias', 'SVrelFreqBias', 'MessageFrameTime',
                      'X', 'dX', 'dX2', 'health',
                      'Y', 'dY', 'dY2', 'FreqNum',
                      'Z', 'dZ', 'dZ2', 'AgeOpInfo']
        elif header['filetype'] == 'E':
            svtype = 'E'  # Galileo
            Nl = 7
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
                    for _, ln in zip(range(Nl), f):
                        pass
                    continue
                elif time > tlim[1]:
                    break
# %% format I2 http://gage.upc.edu/sites/default/files/gLAB/HTML/GPS_Navigation_Rinex_v2.11.html
            svs.append(f'{svtype}{int(ln[:2]):02d}')

            times.append(time)
            """
            now get the data as one big long string per SV
            """
            raw = ln[22:79]  # NOTE: MUST be 79, not 80 due to some files that put \n a character early!
            for i, ln in zip(range(Nl), f):
                raw += ln[STARTCOL2:79]
            # one line per SV
            raws.append(raw.replace('D', 'E').replace('\n', ''))
# %% parse
    # NOTE: must be 'ns' or .to_netcdf will fail!
    t = np.array([np.datetime64(t, 'ns') for t in times])
    nav: xarray.Dataset = None
    svu = sorted(set(svs))

    for sv in svu:
        svi = [i for i, s in enumerate(svs) if s == sv]

        tu = np.unique(t[svi])
        if tu.size != t[svi].size:
            logging.warning(f'duplicate times detected, skipping SV {sv}')
            continue

        darr = np.empty((len(svi), len(fields)))

        for j, i in enumerate(svi):
            darr[j, :] = np.genfromtxt(
                BytesIO(raws[i].encode('ascii')), delimiter=[Lf]*len(fields))

        dsf = {f: (('time', 'sv'), d[:, None])
               for (f, d) in zip(fields, darr.T)}

        if nav is None:
            nav = xarray.Dataset(dsf, coords={'time': t[svi], 'sv': [sv]})
        else:
            nav = xarray.merge((nav,
                                xarray.Dataset(dsf,
                                               coords={'time': t[svi],
                                                       'sv': [sv]})))

    nav.attrs['version'] = header['version']
    nav.attrs['filename'] = fn.name

    return nav


def navheader2(f: TextIO) -> Dict[str, Any]:
    if isinstance(f, Path):
        fn = f
        with fn.open('r') as f:
            return navheader2(f)

# %%verify RINEX version, and that it's NAV
    hdr = rinexinfo(f)
    assert int(hdr['version']) == 2, 'see rinexnav3() for RINEX 3.0 files'

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
