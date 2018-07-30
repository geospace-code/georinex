#!/usr/bin/env python
from pathlib import Path
import xarray
import logging
import numpy as np
from io import BytesIO
from datetime import datetime
from .io import opener, rinexinfo
from typing import Dict, List, Tuple, Any
from typing.io import TextIO
# constants
STARTCOL3 = 4  # column where numerical data starts for RINEX 3


def rinexnav3(fn: Path, tlim: Tuple[datetime, datetime]=None) -> xarray.Dataset:
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
    fields: Dict[str, List[str]] = {}
    times: List[datetime] = []

    with opener(fn) as f:
        header = navheader3(f)
# %% read data
        # these while True are necessary to make EOF work right. not for line in f!
        line = f.readline()
        svtypes = [line[0]]
        while True:
            time = _time(line)

            if tlim is not None:
                if time < tlim[0]:
                    line = _skip(f)
                    if not line or line.startswith('\n'):  # EOF
                        break
                    continue
                elif time > tlim[1]:
                    break

            times.append(time)
# %%
            sv = line[:3]
            field = _newnav(line, sv)

            if sv[0] != svtypes[-1]:
                svtypes.append(sv[0])

            if not sv[0] in fields:
                fields[svtypes[-1]] = field

            svs.append(sv)
# %% get the data as one big long string per SV, unknown # of lines per SV
            raw = line[23:80]  # NOTE: 80, files put data in the last column!

            eof = True
            for line in f:
                if not line.startswith(' '):  # new SV
                    eof = line.startswith('\n')
                    break

                raw += line[STARTCOL3:80]
            # one line per SV
            raws.append(raw.replace('D', 'E').replace('\n', ''))

            if eof:  # EOF
                break
# %% parse
    t = np.array([np.datetime64(t, 'us') for t in times])
    nav: xarray.Dataset = None
    svu = sorted(set(svs))

    for sv in svu:
        svi = np.array([i for i, s in enumerate(svs) if s == sv])

        tu, iu = np.unique(t[svi], return_index=True)
        if tu.size != t[svi].size:
            logging.warning(f'duplicate times detected on SV {sv}, using first of duplicated time(s)')
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
            raise ValueError(f'The data at {tu} is not the same length as the number of fields.')

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

    nav.attrs['version'] = header['version']
    nav.attrs['filename'] = fn.name
    nav.attrs['svtype'] = svtypes

    return nav


def _skip(f: TextIO) -> str:
    for line in f:
        if not line.startswith(' '):  # new SV
            break

    return line


def _time(ln: str) -> datetime:

    return datetime(year=int(ln[4:8]),
                    month=int(ln[9:11]),
                    day=int(ln[12:14]),
                    hour=int(ln[15:17]),
                    minute=int(ln[18:20]),
                    second=int(ln[21:23]))


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
