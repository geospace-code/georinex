from .io import opener
from pathlib import Path
import numpy as np
import logging
from math import ceil
from datetime import datetime
import xarray
from typing import List, Any, Dict, Tuple, Sequence, Optional
from typing.io import TextIO
import psutil
try:
    from pymap3d import ecef2geodetic
except ImportError:
    ecef2geodetic = None


def rinexobs2(fn: Path,
              use: Sequence[str]=None,
              tlim: Tuple[datetime, datetime]=None,
              useindicators: bool=False,
              meas: Sequence[str]=None,
              verbose: bool=False,
              fast: bool=True) -> xarray.Dataset:

    if isinstance(use, str):
        use = [use]

    if use is None or not use[0].strip():
        use = ('C', 'E', 'G', 'J', 'R', 'S')

    obs = None
    for u in use:
        o = rinexsystem2(fn, system=u, tlim=tlim,
                         useindicators=useindicators, meas=meas,
                         verbose=verbose, fast=fast)
        if o is not None:
            if obs is None:
                attrs = o.attrs
                obs = o
            else:
                obs = xarray.merge((obs, o))

    if obs is not None:
        obs.attrs = attrs

    return obs


def rinexsystem2(fn: Path,
                 system: str,
                 tlim: Tuple[datetime, datetime]=None,
                 useindicators: bool=False,
                 meas: Sequence[str]=None,
                 verbose: bool=False,
                 fast: bool=True) -> xarray.Dataset:
    """
    procss RINEX OBS data
    fn: RINEX OBS 2 filename
    system: 'G', 'R', or similar
    meas:  'L1C'  or  ['L1C', 'C1C'] or similar

    fast: speculative preallocation based on minimum SV assumption and file size.
          Avoids double-reading file and more complicated linked lists.
          Believed that Numpy array should be faster than lists anyway.
          Reduce Nsvmin if error (let us know)
    """
    Lf = 14
    assert isinstance(system, str)
# %% allocation
    Nsvsys = 35  # Beidou is 35 max, the current maximum GNSS SV count
    Nsvmin = 6  # based on GPS only, 20 deg. min elev. at poles

    hdr = obsheader2(fn, useindicators, meas)

    if hdr['systems'] != 'M' and system != hdr['systems']:
        return

    if fast:
        Nextra = _fast_alloc(fn, hdr['Nl_sv'])
        fast = isinstance(Nextra, int) and Nextra > 0
        if verbose and not fast:
            logging.info(f'fast mode disabled due to estimation problem, Nextra: {Nextra}')

    if fast:
        times: List[datetime] = []
        """
        estimated number of satellites per file:
            * RINEX OBS2 files have at least one 80-byte line per time: Nsvmin* ceil(Nobs / 5)
        """
        assert isinstance(Nextra, int)
        Nt = ceil(fn.stat().st_size / 80 / (Nsvmin * Nextra))
    else:  # strict preallocation by double-reading file, OK for < 100 MB files
        times = obstime2(fn, verbose=verbose)  # < 10 ms for 24 hour 15 second cadence
        if times is None:
            return

        Nt = len(times)

    Npages = hdr['Nobsused']*3 if useindicators else hdr['Nobsused']

    mem = psutil.virtual_memory()
    memneed = Npages * Nt * Nsvsys * 8  # 8 bytes => 64-bit float
    if memneed > 0.5*mem.available:  # because of array copy Numpy => Xarray
        raise RuntimeError(f'{fn} needs {memneed/1e9} GBytes RAM, but only {mem.available/1e9} Gbytes available \n'
                           'try fast=False to reduce RAM usage, raise a GitHub Issue to let us help')

    data = np.empty((Npages, Nt, Nsvsys))
    if data.size == 0:
        return

    data.fill(np.nan)
# %% start reading
    with opener(fn, verbose=verbose) as f:
        _skip_header(f)

# %% process data
        j = -1  # not enumerate in case of time error
        for ln in f:
            time_epoch = _timeobs(ln)
            if time_epoch is None:
                continue

            if not fast:
                j += 1

            if tlim is not None:
                assert isinstance(tlim[0], datetime), 'time bounds are specified as datetime.datetime'
                if time_epoch < tlim[0]:
                    _skip(f, ln, hdr['Nl_sv'])
                    continue
                elif time_epoch > tlim[1]:
                    break

            if fast:
                j += 1
# %%
            eflag = int(ln[28])
            if eflag not in (0, 1, 5, 6):  # EPOCH FLAG
                logging.info(f'{time_epoch}: epoch flag {eflag}')
                continue

            if verbose:
                print(time_epoch, end="\r")

            if fast:
                times.append(time_epoch)

            try:
                toffset = ln[68:80]
            except ValueError:
                toffset = None
# %% get SV indices
            sv = _getsvind(f, ln)
# %% select one, a few, or all satellites
            iuse = [i for i, s in enumerate(sv) if s[0] == system]
            if len(iuse) == 0:
                _skip(f, ln, hdr['Nl_sv'], sv)
                continue

            gsv = np.array(sv)[iuse]
# %% assign data for each time step
            raws = []
            for i, s in enumerate(sv):
                # don't process discarded satellites
                if s[0] != system:
                    for _ in range(hdr['Nl_sv']):
                        f.readline()
                    continue
                # .rstrip() necessary to handle variety of files and Windows vs. Unix
                # NOT readline(80), but readline()[:80] is needed!
                raw = [f'{f.readline()[:80]:80s}' for _ in range(hdr['Nl_sv'])]  # .rstrip() adds no significant process time

                raws.append(''.join(raw))
            """
            it is about 5x faster to call np.genfromtxt() for all sats and then index,
            vs. calling np.genfromtxt() for each sat.
            """
            # can't use "usecols" with "delimiter"
            # FIXME: only read requested meas=
            darr = np.empty((len(raws), hdr['Nobsused']))
            darr.fill(np.nan)
            for i, r in enumerate(raws):
                for k in range(hdr['Nobs']):
                    v = r[k*(Lf+2):(k+1)*(Lf+2)]

                    if useindicators:
                        if v[:-2].strip():
                            darr[i, k*3] = float(v[:-2])

                        if v[-2].strip():
                            darr[i, k*3+1] = float(v[-2])

                        if v[-1].strip():
                            darr[i, k*3+2] = float(v[-1])
                    else:
                        if v[:-2].strip():
                            darr[i, k] = float(v[:-2])

            assert darr.shape[0] == gsv.size

# %% select only "used" satellites
            isv = [int(s[1:])-1 for s in gsv]
            try:
                for i, k in enumerate(hdr['fields_ind']):
                    if useindicators:
                        data[i*3, j, isv] = darr[:, k*3]
                        # FIXME which other should be excluded?
                        ind = i if meas is not None else k
                        if hdr['fields'][ind] not in ('S1', 'S2'):
                            if hdr['fields'][ind] in ('L1', 'L2'):
                                data[i*3+1, j, isv] = darr[:, k*3+1]

                            data[i*3+2, j, isv] = darr[:, k*3+2]
                    else:
                        data[i, j, isv] = darr[:, k]
            except IndexError as e:
                if fast:
                    raise RuntimeError('this error may be a result of "fast" mode, try fast=False  {e}')
                else:
                    raise
# %% output gathering
    if fast:
        data = data[:, :len(times), :]

    if np.isnan(data).all():  # don't use darr=None sentinel, due to meas= cases
        return

    fields = []
    for field in hdr['fields']:
        fields.append(field)
        if useindicators:
            if field not in ('S1', 'S2'):
                if field in ('L1', 'L2'):
                    fields.append(f'{field}lli')
                else:
                    fields.append(None)
                fields.append(f'{field}ssi')
            else:
                fields.extend([None, None])

    obs = xarray.Dataset(coords={'time': times,
                                 'sv': [f'{system}{i:02d}' for i in range(1, Nsvsys+1)]})

    for i, k in enumerate(fields):
        # FIXME: for limited time span reads, this drops unused data variables
        # if np.isnan(data[i, ...]).all():
            # continue
        if k is None:
            continue
        obs[k] = (('time', 'sv'), data[i, :, :])

    obs = obs.dropna(dim='sv', how='all')
    obs = obs.dropna(dim='time', how='all')  # when tlim specified
# %% attributes
    obs.attrs['filename'] = fn.name
    obs.attrs['version'] = hdr['version']
    obs.attrs['rinextype'] = 'obs'
    obs.attrs['toffset'] = toffset
    obs.attrs['fast_processing'] = int(fast)  # bool is not allowed in NetCDF4

    try:
        obs.attrs['position'] = hdr['position']
        obs.attrs['position_geodetic'] = hdr['position_geodetic']
    except KeyError:
        pass

    return obs


def obsheader2(f: TextIO,
               useindicators: bool=False,
               meas: Sequence[str]=None) -> Dict[str, Any]:

    if isinstance(f, Path):
        fn = f
        with opener(fn, header=True) as f:
            return obsheader2(f, useindicators, meas)

# %% selection
    if isinstance(meas, str):
        meas = [meas]

    if not meas or not meas[0].strip():
        meas = None

    hdr: Dict[str, Any] = {}
    Nobs = 0  # not None due to type checking

    for ln in f:
        if "END OF HEADER" in ln:
            break

        h = ln[60:80].strip()
        c = ln[:60]
# %% measurement types
        if '# / TYPES OF OBSERV' in h:
            if Nobs == 0:
                Nobs = int(c[:6])

            c = c[6:].split()  # NOT within "if Nobs"
# %%
        if h not in hdr:  # Header label
            hdr[h] = c  # string with info
        else:  # concatenate
            if isinstance(hdr[h], str):
                hdr[h] += " " + c
            elif isinstance(hdr[h], list):
                hdr[h] += c
            else:
                raise ValueError(f'not sure what {c} is')
# %% useful values
    hdr['version'] = float(hdr['RINEX VERSION / TYPE'][:9])  # %9.2f
    hdr['systems'] = hdr['RINEX VERSION / TYPE'][40]
    hdr['Nobs'] = Nobs
    hdr['Nl_sv'] = ceil(hdr['Nobs'] / 5)  # 5 observations per line (incorporating LLI, SSI)

# %% list with receiver location in x,y,z cartesian ECEF (OPTIONAL)
    try:
        hdr['position'] = [float(j) for j in hdr['APPROX POSITION XYZ'].split()]
        if ecef2geodetic is not None:
            hdr['position_geodetic'] = ecef2geodetic(*hdr['position'])
    except KeyError:
        pass
# %% observation types
    hdr['fields'] = hdr['# / TYPES OF OBSERV']
    if Nobs != len(hdr['fields']):
        raise ValueError(f'{f.name} header read incorrectly')

    if isinstance(meas, (tuple, list, np.ndarray)):
        ind = np.zeros(len(hdr['fields']), dtype=bool)
        for m in meas:
            for i, f in enumerate(hdr['fields']):
                if f.startswith(m):
                    ind[i] = True

        hdr['fields_ind'] = np.nonzero(ind)[0]
    else:
        ind = slice(None)
        hdr['fields_ind'] = np.arange(Nobs)

    hdr['fields'] = np.array(hdr['fields'])[ind].tolist()

    hdr['Nobsused'] = hdr['Nobs']
    if useindicators:
        hdr['Nobsused'] *= 3

# %%
    if '# OF SATELLITES' in hdr:
        hdr['# OF SATELLITES'] = int(hdr['# OF SATELLITES'][:6])
# %% time
    t0s = hdr['TIME OF FIRST OBS']
    # NOTE: must do second=int(float()) due to non-conforming files
    hdr['t0'] = datetime(year=int(t0s[:6]), month=int(t0s[6:12]), day=int(t0s[12:18]),
                         hour=int(t0s[18:24]), minute=int(t0s[24:30]), second=int(float(t0s[30:36])),
                         microsecond=int(float(t0s[30:43]) % 1 * 1000000))

    try:
        t0s = hdr['TIME OF LAST OBS']
        # NOTE: must do second=int(float()) due to non-conforming files
        hdr['t1'] = datetime(year=int(t0s[:6]), month=int(t0s[6:12]), day=int(t0s[12:18]),
                             hour=int(t0s[18:24]), minute=int(t0s[24:30]), second=int(float(t0s[30:36])),
                             microsecond=int(float(t0s[30:43]) % 1 * 1000000))
    except KeyError:
        pass

    try:  # This key is OPTIONAL
        hdr['interval'] = float(hdr['INTERVAL'][:10])
    except (KeyError, ValueError):
        hdr['interval'] = np.nan  # do NOT set it to None or it breaks NetCDF writing

    return hdr


def _getsvind(f: TextIO, ln: str) -> List[str]:
    Nsv = int(ln[29:32])  # Number of visible satellites this time %i3
    # get first 12 SV ID's
    sv = _getSVlist(ln, min(12, Nsv), [])

    # any more SVs?
    n = Nsv-12
    while n > 0:
        sv = _getSVlist(f.readline(), min(12, n), sv)
        n -= 12

    if Nsv != len(sv):
        raise LookupError('satellite list read incorrectly')

    return sv


def _getSVlist(ln: str, N: int,
               sv: List[str]) -> List[str]:
    """ parse a line of text from RINEX2 SV list"""
    sv.extend([ln[32+i*3:35+i*3] for i in range(N)])

    return sv


def obstime2(fn: Path, verbose: bool=False) -> xarray.DataArray:
    """
    read all times in RINEX2 OBS file
    """
    times = []
    with opener(fn, verbose=verbose) as f:
        # Capture header info
        hdr = obsheader2(f)

        for ln in f:
            time_epoch = _timeobs(ln)
            if time_epoch is None:
                continue

            times.append(time_epoch)

            _skip(f, ln, hdr['Nl_sv'])

    if not times:
        return None

    timedat = xarray.DataArray(times,
                               dims=['time'],
                               attrs={'filename': fn.name,
                                      'interval': hdr['interval']})

    return timedat


def _skip(f: TextIO, ln: str,
          Nl_sv: int,
          sv: Sequence[str]=None):
    """
    skip ahead to next time step
    """
    if sv is None:
        sv = _getsvind(f, ln)

    # f.seek(len(sv)*Nl_sv*80, 1)  # not for io.TextIOWrapper ?
    for _ in range(len(sv)*Nl_sv):
        f.readline()


def _timeobs(ln: str) -> Optional[datetime]:
    """
    Python >= 3.7 supports nanoseconds.  https://www.python.org/dev/peps/pep-0564/
    Python < 3.7 supports microseconds.
    """
    try:
        year = int(ln[1:3])
        if year < 80:
            year += 2000
        else:
            year += 1900

        return datetime(year=year,
                        month=int(ln[4:6]),
                        day=int(ln[7:9]),
                        hour=int(ln[10:12]),
                        minute=int(ln[13:15]),
                        second=int(ln[16:18]),
                        microsecond=int(float(ln[16:26]) % 1 * 1000000)
                        )
    except ValueError:  # garbage between header and RINEX data
        logging.info(f'garbage detected in RINEX file')
        return None


def _skip_header(f: TextIO):
    for ln in f:
        if "END OF HEADER" in ln:
            break


def _fast_alloc(fn: Path, Nl_sv: int) -> Optional[int]:
    """
    prescan first N lines of file to see if it truncates to less than 80 bytes
    Picking N:  N > Nobs+4 or so.  100 seemed a good start.
    """
    assert fn.is_file(), 'need freshly opend file'

    with opener(fn) as f:
        _skip_header(f)

        for ln in f:
            t = _timeobs(ln)
            if isinstance(t, datetime):
                break

        if t is None:
            return None

        _getsvind(f, ln)

        raw = [f.readline() for _ in range(Nl_sv)]

    lens = list(map(len, raw))
    if max(lens) < 79:  # oddly formatted file, no prediction
        return None

    shorts = sum(l < 79 for l in lens)

    return len(lens) - shorts
