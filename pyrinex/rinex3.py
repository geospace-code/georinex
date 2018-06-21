from .io import opener
from pathlib import Path
import numpy as np
from datetime import datetime
from io import BytesIO
import xarray
import logging
from typing import Union, Dict, List, Tuple, Any
from typing.io import TextIO
#
STARTCOL3 = 4  # column where numerical data starts for RINEX 3
"""https://github.com/mvglasow/satstat/wiki/NMEA-IDs"""
SBAS = 100  # offset for ID
GLONASS = 37
QZSS = 192
BEIDOU = 0


def rinexnav3(fn: Path) -> xarray.Dataset:
    """
    Reads RINEX 3.0 NAV files
    Michael Hirsch, Ph.D.
    SciVision, Inc.
    http://www.gage.es/sites/default/files/gLAB/HTML/SBAS_Navigation_Rinex_v3.01.html
    """
    Lf = 19  # string length per field

    fn = Path(fn).expanduser()

    svs = []
    raws = []
    fields: Dict[str, List[str]] = {}
    dt: List[datetime] = []

    with opener(fn) as f:
        """verify RINEX version, and that it's NAV"""
        line = f.readline()
        ver = float(line[:9])
        assert int(ver) == 3, 'see _rinexnav2() for RINEX 3.0 files'
        assert line[20] == 'N', 'Did not detect Nav file'
#        svtype=line[40]
# %% skip header, which has non-constant number of rows
        for line in f:
            if 'END OF HEADER' in line:
                break
# %% read data
        # these while True are necessary to make EOF work right. not for line in f!
        line = f.readline()
        svtypes = [line[0]]
        while True:
            sv, time, field = _newnav(line)
            dt.append(time)

            if sv[0] == 'J':
                print(sv)

            if sv[0] != svtypes[-1]:
                svtypes.append(sv[0])

            if not sv[0] in fields:
                fields[svtypes[-1]] = field

            svs.append(sv)
# %% get the data as one big long string per SV, unknown # of lines per SV
            raw = line[23:80]  # NOTE: 80, files put data in the last column!

            while True:
                line = f.readline().rstrip()
                if not line or line[0] != ' ':  # new SV
                    break

                raw += line[STARTCOL3:80]
            # one line per SV
            raws.append(raw.replace('D', 'E'))

            if not line:  # EOF
                break
# %% parse
    t = np.array([np.datetime64(t, 'ns') for t in dt])
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

    nav.attrs['version'] = ver
    nav.attrs['filename'] = fn.name
    nav.attrs['svtype'] = svtypes

    return nav


def _newnav(ln: str) -> Tuple[str, datetime, List[str]]:
    sv = ln[:3]

    svtype = sv[0]

    if svtype == 'G':
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
    elif svtype == 'C':  # pg A-33  Beidou Compass BDT
        fields = ['SVclockBias', 'SVclockDrift', 'SVclockDriftRate',
                  'AODE', 'Crs', 'DeltaN', 'M0',
                  'Cuc', 'Eccentricity', 'Cus', 'sqrtA',
                  'Toe', 'Cic', 'Omega0', 'Cis',
                  'Io', 'Crc', 'omega', 'OmegaDot',
                  'IDOT', 'BDTWeek',
                  'SVacc', 'SatH1', 'TGD1', 'TGD2',
                  'TransTime', 'AODC']
    elif svtype == 'R':  # pg. A-29   GLONASS
        fields = ['SVclockBias', 'SVrelFreqBias', 'MessageFrameTime',
                  'X', 'dX', 'dX2', 'health',
                  'Y', 'dY', 'dY2', 'FreqNum',
                  'Z', 'dZ', 'dZ2', 'AgeOpInfo']
    elif svtype == 'S':  # pg. A-35 SBAS
        fields = ['SVclockBias', 'SVrelFreqBias', 'MessageFrameTime',
                  'X', 'dX', 'dX2', 'health',
                  'Y', 'dY', 'dY2', 'URA',
                  'Z', 'dZ', 'dZ2', 'IODN']
    elif svtype == 'J':  # pg. A-31  QZSS
        fields = ['SVclockBias', 'SVclockDrift', 'SVclockDriftRate',
                  'IODE', 'Crs', 'DeltaN', 'M0',
                  'Cuc', 'Eccentricity', 'Cus', 'sqrtA',
                  'Toe', 'Cic', 'Omega0', 'Cis',
                  'Io', 'Crc', 'omega', 'OmegaDot',
                  'IDOT', 'CodesL2', 'GPSWeek', 'L2Pflag',
                  'SVacc', 'health', 'TGD', 'IODC',
                  'TransTime', 'FitIntvl']
    elif svtype == 'E':
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

    year = int(ln[4:8])  # I4

    time = datetime(year=year,
                    month=int(ln[9:11]),
                    day=int(ln[12:14]),
                    hour=int(ln[15:17]),
                    minute=int(ln[18:20]),
                    second=int(ln[21:23]))

    return sv, time, fields

# %% OBS


def _scan3(fn: Path, use: Any, verbose: bool=False) -> xarray.Dataset:
    """
    procss RINEX OBS data
    """

    if (not use or not use[0].strip() or
        isinstance(use, str) and use.lower() in ('m', 'all') or
            isinstance(use, (tuple, list, np.ndarray)) and use[0].lower() in ('m', 'all')):

        use = None

    with opener(fn) as f:
        ln = f.readline()
        version = float(ln[:9])  # yes :9
        fields, header, Fmax = _getObsTypes(f, use)

        data: xarray.Dataset = None
    # %% process rest of file
        while True:
            ln = f.readline().rstrip()
            if not ln:
                break

            assert ln[0] == '>'  # pg. A13
            """
            Python >=merge 3.7 supports nanoseconds.  https://www.python.org/dev/peps/pep-0564/
            Python < 3.7 supports microseconds.
            """
            time = datetime(int(ln[2:6]), int(ln[7:9]), int(ln[10:12]),
                            hour=int(ln[13:15]), minute=int(ln[16:18]),
                            second=int(ln[19:21]),
                            microsecond=int(float(ln[19:29]) % 1 * 1000000))
            if verbose:
                print(time, '\r', end="")
# %% get SV indices
            # Number of visible satellites this time %i3  pg. A13
            Nsv = int(ln[33:35])

            sv = []
            raw = ''
            for i in range(Nsv):
                ln = f.readline()
                k = ln[:3]
                sv.append(k)
                raw += ln[3:]

            darr = np.genfromtxt(
                BytesIO(raw.encode('ascii')), delimiter=(14, 1, 1)*Fmax)
# %% assign data for each time step
            for sk in fields:  # for each satellite system type (G,R,S, etc.)
                si = [i for i, s in enumerate(sv) if s[0] in sk]

                garr = darr[si, :]
                gsv = np.array(sv)[si]

                dsf = {}
                for i, k in enumerate(fields[sk]):
                    dsf[k] = (('time', 'sv'), np.atleast_2d(garr[:, i*3]))

                    if k.startswith('L1') or k.startswith('L2'):
                        dsf[k+'lli'] = (('time', 'sv'),
                                        np.atleast_2d(garr[:, i*3+1]))

                    dsf[k+'ssi'] = (('time', 'sv'),
                                    np.atleast_2d(garr[:, i*3+2]))

                if verbose:
                    print(time, '\r', end='')

                if data is None:
                    # , attrs={'toffset':toffset})
                    data = xarray.Dataset(
                        dsf, coords={'time': [time], 'sv': gsv})
                else:
                    if len(fields) == 1:
                        data = xarray.concat((data,
                                              xarray.Dataset(dsf, coords={'time': [time], 'sv': gsv})),
                                             dim='time')
                    else:  # general case, slower for different satellite systems all together
                        data = xarray.merge((data,
                                             xarray.Dataset(dsf, coords={'time': [time], 'sv': gsv})))

    data.attrs['filename'] = f.name
    data.attrs['version'] = version
    # data.attrs['toffset'] = toffset

    return data


def _getObsTypes(f: TextIO, use: Union[str, list, tuple]) -> Tuple[Dict, Dict, int]:
    """ get RINEX 3 OBS types, for each system type"""
    header: Dict[str, Any] = {}
    fields = {}
    Fmax = 0
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
# %% sanity check for Mandatory RINEX 3 headers
    for h in ('APPROX POSITION XYZ',):
        if h not in header:
            raise OSError(
                'Mandatory RINEX 3 headers are missing from file, is it a valid RINEX 3 file?')

    # list with x,y,z cartesian
    header['APPROX POSITION XYZ'] = [float(j) for j in header['APPROX POSITION XYZ'].split()]
# %% select specific satellite systems only (optional)
    if use is not None:
        fields = {k: fields[k] for k in use}

    return fields, header, Fmax
