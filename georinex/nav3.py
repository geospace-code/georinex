#!/usr/bin/env python
from pathlib import Path
import xarray
import logging
import numpy as np
from io import BytesIO
from datetime import datetime
from .io import opener, rinexinfo
from typing import Dict, List, Any, Sequence, Optional
from typing.io import TextIO
# constants
STARTCOL3 = 4  # column where numerical data starts for RINEX 3
Nl = {'C': 7, 'E': 7, 'G': 7, 'J': 7, 'R': 3, 'S': 3}   # number of additional SV lines


def rinexnav3(fn: Path,
              use: Sequence[str]=None,
              tlim: Sequence[datetime]=None) -> xarray.Dataset:
    """
    Reads RINEX 3.x NAV files
    Michael Hirsch, Ph.D.
    SciVision, Inc.
    http://www.gage.es/sites/default/files/gLAB/HTML/SBAS_Navigation_Rinex_v3.01.html

    The "eof" stuff is over detection of files that may or may not have a trailing newline at EOF.
    """
    Lf = 19  # string length per field

    fn = Path(fn).expanduser()

    svs = []
    raws = []
    svtypes: List[str] = []
    fields: Dict[str, List[str]] = {}
    times: List[datetime] = []

    with opener(fn) as f:
        header = navheader3(f)
# %% read data
        for line in f:
            if line.startswith('\n'):  # EOF
                break

            time = _time(line)
            if time is None:  # blank or garbage line
                continue

            if tlim is not None:
                if time < tlim[0] or time > tlim[1]:
                    _skip(f, Nl[line[0]])
                    continue
                # not break due to non-monotonic NAV files

            sv = line[:3]
            if use is not None and not sv[0] in use:
                _skip(f, Nl[sv[0]])
                continue

            times.append(time)
# %% SV types
            field = _newnav(line, sv)

            if len(svtypes) == 0:
                svtypes.append(sv[0])
            elif sv[0] != svtypes[-1]:
                svtypes.append(sv[0])

            if not sv[0] in fields:
                fields[svtypes[-1]] = field

            svs.append(sv)
# %% get the data as one big long string per SV, unknown # of lines per SV
            raw = line[23:80]  # NOTE: 80, files put data in the last column!

            for _, line in zip(range(Nl[sv[0]]), f):
                raw += line[STARTCOL3:80]
            # one line per SV
            raws.append(raw.replace('D', 'E').replace('\n', ''))

    if not raws:
        return None
# %% parse
    # NOTE: must be 'ns' or .to_netcdf will fail!
    t = np.array([np.datetime64(t, 'ns') for t in times])
    nav: xarray.Dataset = None
    svu = sorted(set(svs))

    if len(svu) == 0:
        logging.warning('no specified data found in {fn}')
        return None

    for sv in svu:
        svi = np.array([i for i, s in enumerate(svs) if s == sv])

        tu, iu = np.unique(t[svi], return_index=True)
        if tu.size != t[svi].size:
            logging.warning(f'duplicate times detected on SV {sv}, using first of duplicate times')
            """ I have seen that the data rows match identically when times are duplicated"""
# %% check for optional GPS "fit interval" presence
        cf = fields[sv[0]]
        testread = np.genfromtxt(BytesIO(raws[svi[0]].encode('ascii')), delimiter=Lf)
# %% patching for Spare entries, some receivers include, and some don't include...
        if sv[0] == 'G' and len(cf) == testread.size + 1:
            cf = cf[:-1]
        elif sv[0] == 'C' and len(cf) == testread.size - 1:
            cf.insert(20, 'spare')
        elif sv[0] == 'E' and len(cf) == testread.size - 1:
            cf.insert(22, 'spare')

        if testread.size != len(cf):
            raise ValueError(f'{sv[0]} NAV data @ {tu} is not the same length as the number of fields.')

        darr = np.empty((svi.size, len(cf)))

        for j, i in enumerate(svi):
            darr[j, :] = np.genfromtxt(BytesIO(raws[i].encode('ascii')), delimiter=Lf)

# %% discard duplicated times

        darr = darr[iu, :]

        dsf = {}
        for (f, d) in zip(cf, darr.T):
            if sv[0] in ('R', 'S') and f in ('X', 'dX', 'dX2',
                                             'Y', 'dY', 'dY2',
                                             'Z', 'dZ', 'dZ2'):
                d *= 1000  # km => m

            dsf[f] = (('time', 'sv'), d[:, None])

        if nav is None:
            nav = xarray.Dataset(dsf, coords={'time': tu, 'sv': [sv]})
        else:
            nav = xarray.merge((nav,
                                xarray.Dataset(dsf, coords={'time': tu, 'sv': [sv]})))
# %% patch SV names in case of "G 7" => "G07"
    nav = nav.assign_coords(sv=[s.replace(' ', '0') for s in nav.sv.values.tolist()])
# %% other attributes
    nav.attrs['version'] = header['version']
    nav.attrs['filename'] = fn.name
    nav.attrs['svtype'] = svtypes
    nav.attrs['rinextype'] = 'nav'

    return nav


def _skip(f: TextIO, Nl: int):
    for _, _ in zip(range(Nl), f):
        pass


def _time(ln: str) -> Optional[datetime]:

    try:
        return datetime(year=int(ln[4:8]),
                        month=int(ln[9:11]),
                        day=int(ln[12:14]),
                        hour=int(ln[15:17]),
                        minute=int(ln[18:20]),
                        second=int(ln[21:23]))
    except ValueError:
        return None


def _newnav(ln: str, sv: str) -> List[str]:

    if sv.startswith('G'):
        """
        ftp://igs.org/pub/data/format/rinex303.pdf page A-23 - A-24
        """
        fields = ['SVclockBias', 'SVclockDrift', 'SVclockDriftRate',
                  'IODE', 'Crs', 'DeltaN', 'M0',
                  'Cuc', 'Eccentricity', 'Cus', 'sqrtA',
                  'Toe', 'Cic', 'Omega0', 'Cis',
                  'Io', 'Crc', 'omega', 'OmegaDot',
                  'IDOT', 'CodesL2', 'GPSWeek', 'L2Pflag',
                  'SVacc', 'health', 'TGD', 'IODC',
                  'TransTime', 'FitIntvl']
    elif sv.startswith('C'):  # pg A-33  Beidou Compass BDT
        fields = ['SVclockBias', 'SVclockDrift', 'SVclockDriftRate',
                  'AODE', 'Crs', 'DeltaN', 'M0',
                  'Cuc', 'Eccentricity', 'Cus', 'sqrtA',
                  'Toe', 'Cic', 'Omega0', 'Cis',
                  'Io', 'Crc', 'omega', 'OmegaDot',
                  'IDOT', 'BDTWeek',
                  'SVacc', 'SatH1', 'TGD1', 'TGD2',
                  'TransTime', 'AODC']
    elif sv.startswith('R'):  # pg. A-29   GLONASS
        fields = ['SVclockBias', 'SVrelFreqBias', 'MessageFrameTime',
                  'X', 'dX', 'dX2', 'health',
                  'Y', 'dY', 'dY2', 'FreqNum',
                  'Z', 'dZ', 'dZ2', 'AgeOpInfo']
    elif sv.startswith('S'):  # pg. A-35 SBAS
        fields = ['SVclockBias', 'SVrelFreqBias', 'MessageFrameTime',
                  'X', 'dX', 'dX2', 'health',
                  'Y', 'dY', 'dY2', 'URA',
                  'Z', 'dZ', 'dZ2', 'IODN']
    elif sv.startswith('J'):  # pg. A-31  QZSS
        fields = ['SVclockBias', 'SVclockDrift', 'SVclockDriftRate',
                  'IODE', 'Crs', 'DeltaN', 'M0',
                  'Cuc', 'Eccentricity', 'Cus', 'sqrtA',
                  'Toe', 'Cic', 'Omega0', 'Cis',
                  'Io', 'Crc', 'omega', 'OmegaDot',
                  'IDOT', 'CodesL2', 'GPSWeek', 'L2Pflag',
                  'SVacc', 'health', 'TGD', 'IODC',
                  'TransTime', 'FitIntvl']
    elif sv.startswith('E'):  # pg. A-25 Galileo Table A8
        fields = ['SVclockBias', 'SVclockDrift', 'SVclockDriftRate',
                  'IODnav', 'Crs', 'DeltaN', 'M0',
                  'Cuc', 'Eccentricity', 'Cus', 'sqrtA',
                  'Toe', 'Cic', 'Omega0', 'Cis',
                  'Io', 'Crc', 'omega', 'OmegaDot',
                  'IDOT', 'DataSrc', 'GALWeek',
                  'SISA', 'health', 'BGDe5a', 'BGDe5b',
                  'TransTime']
    else:
        raise ValueError(f'Unknown SV type {sv[0]}')

    return fields


def navheader3(f: TextIO) -> Dict[str, Any]:
    if isinstance(f, Path):
        fn = f
        with fn.open('r') as f:
            return navheader3(f)

    hdr = rinexinfo(f)
    assert int(hdr['version']) == 3, 'see rinexnav2() for RINEX 2.x files'
    assert hdr['filetype'] == 'N', 'Did not detect Nav file'

    for ln in f:
        if 'END OF HEADER' in ln:
            break

        hdr[ln[60:]] = ln[:60]

    return hdr


def navtime3(fn: Path) -> xarray.DataArray:
    """
    return all times in RINEX file
    """
    times = []

    with opener(fn) as f:
        navheader3(f)  # skip header

        for line in f:
            time = _time(line)
            if not time:
                continue

            times.append(time)
            _skip(f, Nl[line[0]])  # different system types skip different line counts

    if not times:
        return None

    times = np.unique(times)

    timedat = xarray.DataArray(times,
                               dims=['time'],
                               attrs={'filename': fn})

    return timedat
