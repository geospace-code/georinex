#!/usr/bin/env python
from pathlib import Path
import xarray
import logging
import numpy as np
import math
from datetime import datetime
from typing import Dict, Union, List, Any, Sequence
from typing.io import TextIO
#
from .io import opener, rinexinfo
from .common import rinex_string_to_float
# constants
STARTCOL3 = 4  # column where numerical data starts for RINEX 3
Nl = {'C': 7, 'E': 7, 'G': 7, 'J': 7, 'R': 3, 'S': 3}   # number of additional SV lines
Lf = 19  # string length per field


def rinexnav3(fn: Union[TextIO, str, Path],
              use: Sequence[str] = None,
              tlim: Sequence[datetime] = None) -> xarray.Dataset:
    """
    Reads RINEX 3.x NAV files
    Michael Hirsch, Ph.D.
    SciVision, Inc.
    http://www.gage.es/sites/default/files/gLAB/HTML/SBAS_Navigation_Rinex_v3.01.html

    The "eof" stuff is over detection of files that may or may not have a trailing newline at EOF.
    """
    if isinstance(fn, (str, Path)):
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

            try:
                time = _time(line)
            except ValueError:  # blank or garbage line
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

# %% parse
    # NOTE: must be 'ns' or .to_netcdf will fail!
    t = np.array([np.datetime64(t, 'ns') for t in times])
    nav = xarray.Dataset({}, coords={'time': [], 'sv': []})
    svu = sorted(set(svs))

    for sv in svu:
        svi = np.array([i for i, s in enumerate(svs) if s == sv])

        tu, iu = np.unique(t[svi], return_index=True)
        if tu.size != t[svi].size:
            logging.info(f'duplicate times detected on SV {sv}, using first of duplicate times')
            """ I have seen that the data rows match identically when times are duplicated"""

        cf = _sparefields(fields[sv[0]], sv[0], raws[svi[0]])
        gi = [i for i, c in enumerate(cf) if not c.startswith(('spare', 'FitIntvl'))]
        darr = np.empty((svi.size, len(gi)))

        for j, i in enumerate(svi):
            # darr[j, :] = np.genfromtxt(io.BytesIO(raws[i].encode('ascii')), delimiter=Lf)
            try:
                darr[j, :] = [float(raws[i][Lf*k:Lf*(k+1)]) for k in gi]
            except ValueError:
                logging.info(f'malformed line for {sv}')
                darr[j, :] = np.nan
# %% discard duplicated times

        darr = darr[iu, :]

        dsf = {}
        for (i, d) in zip(gi, darr.T):
            if sv[0] in ('R', 'S') and cf[i] in ('X', 'dX', 'dX2',
                                                 'Y', 'dY', 'dY2',
                                                 'Z', 'dZ', 'dZ2'):
                d *= 1000  # km => m

            dsf[cf[i]] = (('time', 'sv'), d[:, None])

        if len(nav) == 0:
            nav = xarray.Dataset(dsf, coords={'time': tu, 'sv': [sv]})
        else:
            nav = xarray.merge((nav,
                                xarray.Dataset(dsf, coords={'time': tu, 'sv': [sv]})))
# %% patch SV names in case of "G 7" => "G07"
    nav = nav.assign_coords(sv=[s.replace(' ', '0') for s in nav.sv.values.tolist()])
# %% other attributes

    # Add ionospheric correction coefficients if exist.
    if 'IONOSPHERIC CORR' in header:
        corr = header['IONOSPHERIC CORR']
        if 'GPSA' in corr and 'GPSB' in corr:
            nav.attrs['ionospheric_corr_GPS'] = np.hstack((corr['GPSA'],
                                                           corr['GPSB']))
        if 'GAL' in corr:
            nav.attrs['ionospheric_corr_GAL'] = corr['GAL']
        if 'QZSA' in corr and 'QZSB' in corr:
            nav.attrs['ionospheric_corr_QZS'] = np.hstack((corr['QZSA'],
                                                           corr['QZSB']))
        if 'BDSA' in corr and 'BDSB' in corr:
            nav.attrs['ionospheric_corr_BDS'] = np.hstack((corr['BDSA'],
                                                           corr['BDSB']))
        if 'IRNA' in corr and 'IRNB' in corr:
            nav.attrs['ionospheric_corr_BDS'] = np.hstack((corr['IRNA'],
                                                           corr['IRNB']))

    nav.attrs['version'] = header['version']
    nav.attrs['svtype'] = svtypes
    nav.attrs['rinextype'] = 'nav'
    if isinstance(fn, Path):
        nav.attrs['filename'] = fn.name

    return nav


def _skip(f: TextIO, Nl: int):
    for _, _ in zip(range(Nl), f):
        pass


def _time(ln: str) -> datetime:

    return datetime(year=int(ln[4:8]),
                    month=int(ln[9:11]),
                    day=int(ln[12:14]),
                    hour=int(ln[15:17]),
                    minute=int(ln[18:20]),
                    second=int(ln[21:23]))


def _sparefields(cf: List[str], sys: str, raw: str) -> List[str]:
    """
    check for optional spare fields, or GPS "fit interval" field

    You might find a new way that NAV3 files are irregular--please open a
    GitHub Issue or Pull Request.
    """
    numval = math.ceil(len(raw) / Lf)  # need this for irregularly defined files
# %% patching for Spare entries, some receivers include, and some don't include...
    if sys == 'G':
        if numval == 30:
            cf = cf[:-1]
        elif numval == 29:
            cf = cf[:-2]
    elif sys == 'C':
        if numval == 27:
            cf = cf[:20] + [cf[21]] + cf[23:29]
        elif numval == 28:
            cf = cf[:22] + cf[23:29]
        elif numval == 29:
            cf = cf[:29]
        elif numval == 30:
            cf = cf[:30]
    elif sys == 'J':
        if numval == 29:
            cf = cf[:29]
        elif numval == 30:
            cf = cf[:30]
    elif sys == 'E':
        if numval == 29:  # only one trailing spare fields
            cf = cf[:-2]
        elif numval == 28:  # zero trailing spare fields
            cf = cf[:-3]
        elif numval == 27:  # no middle or trailing spare fields
            cf = cf[:22] + cf[23:-3]
    elif sys == 'I':
        if numval == 28:
            cf = cf[:28]

    if numval != len(cf):
        raise ValueError(f'System {sys} NAV data is not the same length as the number of fields.')

    return cf


def _newnav(ln: str, sv: str) -> List[str]:

    if sv.startswith('G'):
        """
        ftp://igs.org/pub/data/format/rinex303.pdf

        pages:
        G: A23-A24
        E: A25-A28
        R: A29-A30
        J: A31-A32
        C: A33-A34
        S: A35-A36
        I: A37-A39
        """
        fields = ['SVclockBias', 'SVclockDrift', 'SVclockDriftRate',
                  'IODE', 'Crs', 'DeltaN', 'M0',
                  'Cuc', 'Eccentricity', 'Cus', 'sqrtA',
                  'Toe', 'Cic', 'Omega0', 'Cis',
                  'Io', 'Crc', 'omega', 'OmegaDot',
                  'IDOT', 'CodesL2', 'GPSWeek', 'L2Pflag',
                  'SVacc', 'health', 'TGD', 'IODC',
                  'TransTime', 'FitIntvl', 'spare0', 'spare1']
        assert len(fields) == 31
    elif sv.startswith('C'):  # pg A-33  Beidou Compass BDT
        fields = ['SVclockBias', 'SVclockDrift', 'SVclockDriftRate',
                  'AODE', 'Crs', 'DeltaN', 'M0',
                  'Cuc', 'Eccentricity', 'Cus', 'sqrtA',
                  'Toe', 'Cic', 'Omega0', 'Cis',
                  'Io', 'Crc', 'omega', 'OmegaDot',
                  'IDOT', 'spare0', 'BDTWeek', 'spare1',
                  'SVacc', 'SatH1', 'TGD1', 'TGD2',
                  'TransTime', 'AODC', 'spare2', 'spare3']
        assert len(fields) == 31
    elif sv.startswith('R'):  # pg. A-29   GLONASS
        fields = ['SVclockBias', 'SVrelFreqBias', 'MessageFrameTime',
                  'X', 'dX', 'dX2', 'health',
                  'Y', 'dY', 'dY2', 'FreqNum',
                  'Z', 'dZ', 'dZ2', 'AgeOpInfo']
        assert len(fields) == 15
    elif sv.startswith('S'):  # pg. A-35 SBAS
        fields = ['SVclockBias', 'SVrelFreqBias', 'MessageFrameTime',
                  'X', 'dX', 'dX2', 'health',
                  'Y', 'dY', 'dY2', 'URA',
                  'Z', 'dZ', 'dZ2', 'IODN']
        assert len(fields) == 15
    elif sv.startswith('J'):  # pg. A-31  QZSS
        fields = ['SVclockBias', 'SVclockDrift', 'SVclockDriftRate',
                  'IODE', 'Crs', 'DeltaN', 'M0',
                  'Cuc', 'Eccentricity', 'Cus', 'sqrtA',
                  'Toe', 'Cic', 'Omega0', 'Cis',
                  'Io', 'Crc', 'omega', 'OmegaDot',
                  'IDOT', 'CodesL2', 'GPSWeek', 'L2Pflag',
                  'SVacc', 'health', 'TGD', 'IODC',
                  'TransTime', 'FitIntvl', 'spare0', 'spare1']
        assert len(fields) == 31
    elif sv.startswith('E'):  # pg. A-25 Galileo Table A8
        fields = ['SVclockBias', 'SVclockDrift', 'SVclockDriftRate',
                  'IODnav', 'Crs', 'DeltaN', 'M0',
                  'Cuc', 'Eccentricity', 'Cus', 'sqrtA',
                  'Toe', 'Cic', 'Omega0', 'Cis',
                  'Io', 'Crc', 'omega', 'OmegaDot',
                  'IDOT', 'DataSrc', 'GALWeek',
                  'spare0',
                  'SISA', 'health', 'BGDe5a', 'BGDe5b',
                  'TransTime',
                  'spare1', 'spare2', 'spare3']
        assert len(fields) == 31
    elif sv.startswith('I'):
        fields = ['SVclockBias', 'SVclockDrift', 'SVclockDriftRate',
                  'IODEC', 'Crs', 'DeltaN', 'M0',
                  'Cuc', 'Eccentricity', 'Cus', 'sqrtA',
                  'Toe', 'Cic', 'Omega0', 'Cis',
                  'Io', 'Crc', 'omega', 'OmegaDot',
                  'IDOT', 'spare0', 'BDTWeek', 'spare1',
                  'URA', 'health', 'TGD', 'spare2',
                  'TransTime',
                  'spare3', 'spare4', 'spare5']
        assert len(fields) == 31
    else:
        raise ValueError(f'Unknown SV type {sv[0]}')

    return fields


def navheader3(f: TextIO) -> Dict[str, Any]:

    if isinstance(f, (str, Path)):
        with opener(f, header=True) as h:
            return navheader3(h)

    hdr = rinexinfo(f)

    for ln in f:
        if 'END OF HEADER' in ln:
            break

        kind, content = ln[60:].strip(), ln[:60]
        if kind == "IONOSPHERIC CORR":
            if kind not in hdr:
                hdr[kind] = {}

            coeff_kind = content[:4].strip()
            N = 3 if coeff_kind == 'GAL' else 4
            # RINEX 3.04 table A5 page A19
            coeff = [rinex_string_to_float(content[5 + i*12:5 + (i+1)*12]) for i in range(N)]
            hdr[kind][coeff_kind] = coeff
        else:
            hdr[kind] = content

    return hdr


def navtime3(fn: Union[TextIO, Path]) -> np.ndarray:
    """
    return all times in RINEX file
    """
    times = []

    with opener(fn) as f:
        navheader3(f)  # skip header

        for line in f:
            try:
                time = _time(line)
            except ValueError:
                continue

            times.append(time)
            _skip(f, Nl[line[0]])  # different system types skip different line counts

    return np.unique(times)
