from .io import opener
from pathlib import Path
import numpy as np
import logging
from math import ceil
from datetime import datetime
import xarray
from typing import List, Any, Dict, Tuple, Sequence, Optional
from typing.io import TextIO
try:
    from pymap3d import ecef2geodetic
except ImportError:
    ecef2geodetic = None


def rinexobs2(fn: Path,
              use: Sequence[str]=None,
              tlim: Tuple[datetime, datetime]=None,
              useindicators: bool=False,
              meas: Sequence[str]=None,
              verbose: bool=False) -> xarray.Dataset:

    if isinstance(use, str):
        use = [use]

    if use is None or not use[0].strip():
        use = ('C', 'E', 'G', 'J', 'R', 'S')

    obs = None
    for u in use:
        o = rinexsystem2(fn, system=u, tlim=tlim,
                         useindicators=useindicators, meas=meas, verbose=verbose)
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
                 verbose: bool=False) -> xarray.Dataset:
    """
    procss RINEX OBS data
    fn: RINEX OBS 2 filename
    system: 'G', 'R', or similar
    meas:  'L1C'  or  ['L1C', 'C1C'] or similar
    """
    Lf = 14
    assert isinstance(system, str)
# %% allocation
    Nsvmax = 32  # FIXME per each system.
    times = obstime2(fn, verbose=verbose)  # < 10 ms for 24 hour 15 second cadence
    if times is None:
        return

    hdr = obsheader2(fn, useindicators, meas)

    if hdr['systems'] != 'M' and system != hdr['systems']:
        return

    Nl_sv = ceil(hdr['Nobs']/5)

    Npages = hdr['Nobsused']*3 if useindicators else hdr['Nobsused']
    data = np.empty((Npages, times.size, Nsvmax))
    if data.size == 0:
        return

    data.fill(np.nan)


# %% start reading
    with opener(fn, verbose=verbose) as f:
        # skip header
        for ln in f:
            if 'END OF HEADER' in ln:
                break

# %% process data
        j = -1  # not enumerate in case of time error
        for ln in f:
            time_epoch = _timeobs(ln)
            if time_epoch is None:
                continue

            j += 1

            if tlim is not None:
                assert isinstance(tlim[0], datetime), 'time bounds are specified as datetime.datetime'
                if time_epoch < tlim[0]:
                    _skip(f, ln, hdr['Nobs'])
                    continue
                elif time_epoch > tlim[1]:
                    break
# %%
            eflag = int(ln[28])
            if eflag not in (0, 1, 5, 6):  # EPOCH FLAG
                logging.info(f'{time_epoch}: epoch flag {eflag}')
                continue

            if verbose:
                print(time_epoch, end="\r")

            try:
                toffset = ln[68:80]
            except ValueError:
                toffset = None
# %% get SV indices
            sv = _getsvind(f, ln)
# %% select one, a few, or all satellites
            iuse = [i for i, s in enumerate(sv) if s[0] == system]
            if len(iuse) == 0:
                _skip(f, ln, hdr['Nobs'], sv)
                continue

            gsv = np.array(sv)[iuse]
# %% assign data for each time step
            raws = []
            for i, s in enumerate(sv):
                # don't process discarded satellites
                if not s[0] == system:
                    for _ in range(Nl_sv):
                        f.readline()
                    continue
                # .rstrip() necessary to handle variety of files and Windows vs. Unix
                raw = ''
                for _ in range(Nl_sv):
                    raw += f'{f.readline()[:80].rstrip():80s}'

                raws.append(raw)
            """
            it is about 5x faster to call np.genfromtxt() for all sats and then index,
            vs. calling np.genfromtxt() for each sat.
            """
            # can't use "usecols" with "delimiter"
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
# %% output gathering
    if np.isnan(data).all():
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
                                 'sv': [f'{system}{i:02d}' for i in range(1, Nsvmax+1)]})

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

    for l in f:
        if "END OF HEADER" in l:
            break

        h = l[60:80].strip()
        c = l[:60]
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
        Nobs = hdr['Nobs']

        for ln in f:
            time_epoch = _timeobs(ln)
            if time_epoch is None:
                continue

            times.append(time_epoch)

            _skip(f, ln, Nobs)

    if not times:
        return None

    timedat = xarray.DataArray(times,
                               dims=['time'],
                               attrs={'filename': fn.name,
                                      'interval': hdr['interval']})

    return timedat


def _skip(f: TextIO, ln: str,
          Nobs: int,
          sv: Sequence[str]=None):
    """
    skip ahead to next time step
    """
    if sv is None:
        sv = _getsvind(f, ln)

    Nl_sv = ceil(Nobs/5)

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
