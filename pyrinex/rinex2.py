from .io import opener
from pathlib import Path
import numpy as np
from math import ceil
from datetime import datetime
from io import BytesIO
import xarray
from typing import Union, List, Any, Dict
import logging
#
STARTCOL2 = 3  # column where numerical data starts for RINEX 2


def rinexnav2(fn: Path) -> xarray.Dataset:
    """
    Reads RINEX 2.11 NAV files
    Michael Hirsch, Ph.D.
    SciVision, Inc.

    http://gage14.upc.es/gLAB/HTML/GPS_Navigation_Rinex_v2.11.html
    ftp://igs.org/pub/data/format/rinex211.txt
    """
    fn = Path(fn).expanduser()

    Nl = 7  # number of additional lines per record, for RINEX 2 NAV
    Lf = 19  # string length per field

    svs = []
    dt: List[datetime] = []
    raws = []

    with opener(fn) as f:
        """verify RINEX version, and that it's NAV"""
        line = f.readline()
        ver = float(line[:9])  # yes :9
        assert int(ver) == 2, 'see _rinexnav3() for RINEX 3.0 files'

        if line[20] == 'N':
            svtype = 'G'
            fields = ['SVclockBias', 'SVclockDrift', 'SVclockDriftRate', 'IODE', 'Crs', 'DeltaN',
                      'M0', 'Cuc', 'Eccentricity', 'Cus', 'sqrtA', 'Toe', 'Cic', 'Omega0', 'Cis', 'Io',
                      'Crc', 'omega', 'OmegaDot', 'IDOT', 'CodesL2', 'GPSWeek', 'L2Pflag', 'SVacc',
                      'health', 'TGD', 'IODC', 'TransTime', 'FitIntvl']
        elif line[20] == 'G':
            svtype = 'R'  # GLONASS
            fields = ['SVclockBias', 'SVrelFreqBias', 'MessageFrameTime',
                      'X', 'dX', 'dX2', 'health',
                      'Y', 'dY', 'dY2', 'FreqNum',
                      'Z', 'dZ', 'dZ2', 'AgeOpInfo']
        else:
            raise NotImplementedError(f'I do not yet handle Rinex 2 NAV {line}')

# %% skip header, which has non-constant number of rows
        while True:
            if 'END OF HEADER' in f.readline():
                break
# %% read data
        for ln in f:
            # format I2 http://gage.upc.edu/sites/default/files/gLAB/HTML/GPS_Navigation_Rinex_v2.11.html
            svs.append(f'{svtype}{int(ln[:2]):02d}')
            # format I2
            dt.append(_obstime([ln[3:5], ln[6:8], ln[9:11],
                               ln[12:14], ln[15:17], ln[17:20], ln[17:22]]))
            """
            now get the data as one big long string per SV
            """
            raw = ln[22:79]  # NOTE: MUST be 79, not 80 due to some files that put \n a character early!
            for _ in range(Nl):
                raw += f.readline()[STARTCOL2:79]
            # one line per SV
            raws.append(raw.replace('D', 'E'))
# %% parse
    t = np.array([np.datetime64(t, 'ns') for t in dt])
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

    nav.attrs['version'] = ver
    nav.attrs['filename'] = fn.name

    return nav


def _scan2(fn: Path, use: Any, verbose: bool=False) -> xarray.Dataset:
    """
     procss RINEX OBS data
    """
    Lf = 14

    if (not use or not use[0].strip() or
        isinstance(use, str) and use.lower() in ('m', 'all') or
            isinstance(use, (tuple, list, np.ndarray)) and use[0].lower() in ('m', 'all')):

        use = None

    with opener(fn) as f:
        header: Dict[str, Any] = {}
        Nobs = None
        # Capture header info
        for l in f:
            if "END OF HEADER" in l:
                break

            h = l[60:80]
            c = l[:60]
            if '# / TYPES OF OBSERV' in h:
                if Nobs is None:
                    Nobs = int(c[:6])
                    c = c[6:]

            if h.strip() not in header:  # Header label
                header[h.strip()] = c
                # string with info
            else:
                header[h.strip()] += " " + c
                # concatenate to the existing string
# %% sanity check that MANDATORY RINEX 2 headers exist
        for h in ('RINEX VERSION / TYPE', 'APPROX POSITION XYZ', 'INTERVAL'):
            if h not in header:
                raise OSError(f'Mandatory RINEX 2 headers are missing from {fn}'
                              ' is it a valid RINEX 2 file?')
# %% file seems OK, keep processing
        verRinex = float(header['RINEX VERSION / TYPE'][:9])  # %9.2f
        # list with x,y,z cartesian
        header['APPROX POSITION XYZ'] = [
            float(j) for j in header['APPROX POSITION XYZ'].split()]
        # observation types
        fields = header['# / TYPES OF OBSERV'].split()
        assert Nobs == len(fields), 'header read incorrectly'

        header['INTERVAL'] = float(header['INTERVAL'][:10])

        data: xarray.Dataset = None
# %% process rest of file
        while True:
            ln = f.readline()
            if not ln:
                break

            eflag = int(ln[28])
            if eflag not in (0, 1, 5, 6):  # EPOCH FLAG
                print(eflag)
                continue

            time = _obstime(
                [ln[1:3],  ln[4:6], ln[7:9],  ln[10:12], ln[13:15], ln[16:26]])
            if verbose:
                print(time, '\r', end="")

            try:
                toffset = ln[68:80]
            except ValueError:
                toffset = None
# %% get SV indices
            Nsv = int(ln[29:32])  # Number of visible satellites this time %i3
            # get first 12 SV ID's
            sv = _getSVlist(ln, min(12, Nsv), [])

            # any more SVs?
            n = Nsv-12
            while n > 0:
                ln = f.readline()
                sv = _getSVlist(ln, min(12, n), sv)
                n -= 12
            assert Nsv == len(sv), 'satellite list read incorrectly'
# %% select one, a few, or all satellites
            iuse: Union[List[int], slice]
            if use is not None:
                iuse = [i for i, s in enumerate(sv) if s[0] in use]
            else:
                iuse = slice(None)

            gsv = np.array(sv)[iuse]
# %% assign data for each time step
            darr = np.empty((Nsv, Nobs*3))
            Nl_sv = int(ceil(Nobs/5))  # CEIL needed for Py27 only.

            for i, s in enumerate(sv):
                raw = ''
                for _ in range(Nl_sv):
                    raw += f.readline()[:80]

                # save a lot of time by not processing discarded satellites
                if use is not None and not s[0] in use:
                    continue

                # some files truncate and put \n in data space.
                raw = raw.replace('\n', ' ')

                darr[i, :] = np.genfromtxt(
                    BytesIO(raw.encode('ascii')), delimiter=[Lf, 1, 1]*Nobs)
# % select only "used" satellites
            garr = darr[iuse, :]
            dsf = {}
            for i, k in enumerate(fields):
                dsf[k] = (('time', 'sv'), np.atleast_2d(garr[:, i*3]))
                if k not in ('S1', 'S2'):  # FIXME which other should be excluded?
                    if k in ('L1', 'L2'):
                        dsf[k+'lli'] = (('time', 'sv'),
                                        np.atleast_2d(garr[:, i*3+1]))
                    dsf[k+'ssi'] = (('time', 'sv'),
                                    np.atleast_2d(garr[:, i*3+2]))

            if data is None:
                data = xarray.Dataset(dsf, coords={'time': [time], 'sv': gsv}, attrs={
                                      'toffset': toffset})
            else:
                data = xarray.concat((data,
                                      xarray.Dataset(dsf, coords={'time': [time], 'sv': gsv}, attrs={'toffset': toffset})),
                                     dim='time')

        data.attrs['filename'] = f.name
        data.attrs['version'] = verRinex

        return data


def _getSVlist(ln: str, N: int, sv: list) -> list:
    """ parse a line of text from RINEX2 SV list"""
    for i in range(N):
        s = ln[32+i*3:35+i*3].strip()
        if not s.strip():
            raise ValueError(f'did not get satellite names from {ln}')
        sv.append(s)

    return sv


def _obstime(fol: List[str]) -> datetime:
    """
    Python >= 3.7 supports nanoseconds.  https://www.python.org/dev/peps/pep-0564/
    Python < 3.7 supports microseconds.
    """
    year = int(fol[0])
    if 80 <= year <= 99:
        year += 1900
    elif year < 80:  # because we might pass in four-digit year
        year += 2000

    return datetime(year=year, month=int(fol[1]), day=int(fol[2]),
                    hour=int(fol[3]), minute=int(fol[4]),
                    second=int(float(fol[5])),
                    microsecond=int(float(fol[5]) % 1 * 1000000)
                    )
