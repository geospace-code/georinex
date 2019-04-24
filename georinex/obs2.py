from pathlib import Path
import numpy as np
import logging
import io
from math import ceil
from datetime import datetime, timedelta
import xarray
from typing import List, Union, Any, Dict, Tuple, Sequence, Optional
from typing.io import TextIO
try:
    from pymap3d import ecef2geodetic
except ImportError:
    ecef2geodetic = None

from .io import opener, rinexinfo
from .common import determine_time_system, check_ram, _check_time_interval, check_unique_times


def rinexobs2(fn: Path,
              use: Sequence[str] = None,
              tlim: Tuple[datetime, datetime] = None,
              useindicators: bool = False,
              meas: Sequence[str] = None,
              verbose: bool = False,
              *,
              fast: bool = True,
              interval: Union[float, int, timedelta] = None) -> xarray.Dataset:

    if isinstance(use, str):
        use = [use]

    if use is None or not use[0].strip():
        use = ('C', 'E', 'G', 'J', 'R', 'S')

    obs = xarray.Dataset({}, coords={'time': [], 'sv': []})
    attrs: Dict[str, Any] = {}
    for u in use:
        o = rinexsystem2(fn, system=u, tlim=tlim,
                         useindicators=useindicators, meas=meas,
                         verbose=verbose,
                         fast=fast, interval=interval)
        if len(o) > 0:
            attrs = o.attrs
            obs = xarray.merge((obs, o))

    obs.attrs = attrs

    return obs


def rinexsystem2(fn: Union[TextIO, Path],
                 system: str,
                 tlim: Tuple[datetime, datetime] = None,
                 useindicators: bool = False,
                 meas: Sequence[str] = None,
                 verbose: bool = False,
                 *,
                 fast: bool = True,
                 interval: Union[float, int, timedelta] = None) -> xarray.Dataset:
    """
    process RINEX OBS data

    fn: RINEX OBS 2 filename
    system: 'G', 'R', or similar

    tlim: read between these time bounds
    useindicators: SSI, LLI are output
    meas:  'L1C'  or  ['L1C', 'C1C'] or similar

    fast: speculative preallocation based on minimum SV assumption and file size.
          Avoids double-reading file and more complicated linked lists.
          Believed that Numpy array should be faster than lists anyway.
          Reduce Nsvmin if error (let us know)

    t_interval: allows decimating file read by time e.g. every 5 seconds.
                Useful to speed up reading of very large RINEX files
    """
    Lf = 14
    if not isinstance(system, str):
        raise TypeError('System type() must be str')

    if tlim is not None and not isinstance(tlim[0], datetime):
        raise TypeError('time bounds are specified as datetime.datetime')

    interval = _check_time_interval(interval)
# %% allocation
    # these values are not perfect, but seem reasonable.
    # Let us know if you needed to change them.
    Nsvsys = 35  # Beidou is 35 max, the current maximum GNSS SV count

    hdr = obsheader2(fn, useindicators, meas)

    if hdr['systems'] != 'M' and system != hdr['systems']:
        logging.debug(f'system {system} in {fn} was not present')
        return xarray.Dataset({})
# %% preallocate
    if fast:
        Nextra = _fast_alloc(fn, hdr['Nl_sv'])
        fast = Nextra > 0
        if verbose and not fast:
            logging.info(f'fast mode disabled due to estimation problem, Nextra: {Nextra}')
    else:
        Nextra = 0

    times = _num_times(fn, Nextra, tlim, verbose)
    Nt = times.size

    Npages = hdr['Nobsused']*3 if useindicators else hdr['Nobsused']

    memneed = Npages * Nt * Nsvsys * 8  # 8 bytes => 64-bit float
    check_ram(memneed, fn)
    data = np.empty((Npages, Nt, Nsvsys))
    data.fill(np.nan)
# %% start reading
    with opener(fn) as f:
        _skip_header(f)

# %% process data
        j = -1  # not enumerate in case of time error
        last_epoch = None
# %% time handling / skipping
        for ln in f:
            try:
                time_epoch = _timeobs(ln)
            except ValueError:
                continue

            if tlim is not None:
                if time_epoch < tlim[0]:  # before specified start-time
                    _skip(f, ln, hdr['Nl_sv'])
                    continue
                elif time_epoch > tlim[1]:  # reached end-time of read
                    break

            if interval is not None:
                if last_epoch is None:  # initialization
                    last_epoch = time_epoch
                else:
                    if time_epoch - last_epoch < interval:
                        _skip(f, ln, hdr['Nl_sv'])
                        continue
                    else:
                        last_epoch += interval

# %% j += 1 must be after all time skipping
            j += 1

            if verbose:
                print(time_epoch, end="\r")

            if fast:
                try:
                    times[j] = time_epoch
                except IndexError as e:
                    raise IndexError(f'may be "fast" mode bug, try fast=False or "-strict" command-line option {e}')
# %% Does anyone need this?
#            try:
#                toffset = ln[68:80]
#            except ValueError:
#                pass
# %% get SV indices
            try:
                sv = _getsvind(f, ln)
            except ValueError as e:
                logging.debug(e)
                continue
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

            for i, k in enumerate(hdr['fields_ind']):
                if useindicators:
                    data[i*3, j, isv] = darr[:, k*3]
                    # FIXME which other should be excluded?
                    ind = i if meas is not None else k
                    if not hdr['fields'][ind].startswith('S'):
                        if hdr['fields'][ind].startswith('L'):
                            data[i*3+1, j, isv] = darr[:, k*3+1]

                        data[i*3+2, j, isv] = darr[:, k*3+2]
                else:
                    data[i, j, isv] = darr[:, k]
# %% output gathering
    data = data[:, :times.size, :]  # trims down for unneeded preallocated

    fields = []
    for field in hdr['fields']:
        fields.append(field)
        if useindicators:
            if field not in ('S1', 'S2', 'S5'):
                if field in ('L1', 'L2', 'L5'):
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
        #     continue
        if k is None:
            continue
        obs[k] = (('time', 'sv'), data[i, :, :])

    obs = obs.dropna(dim='sv', how='all')
    obs = obs.dropna(dim='time', how='all')  # when tlim specified
# %% attributes
    obs.attrs['version'] = hdr['version']
    obs.attrs['rinextype'] = 'obs'
    obs.attrs['fast_processing'] = int(fast)  # bool is not allowed in NetCDF4
    obs.attrs['time_system'] = determine_time_system(hdr)
    if isinstance(fn, Path):
        obs.attrs['filename'] = fn.name

    try:
        obs.attrs['position'] = hdr['position']
        obs.attrs['position_geodetic'] = hdr['position_geodetic']
    except KeyError:
        pass

    return obs


def _num_times(fn: Path, Nextra: int,
               tlim: Optional[Tuple[datetime, datetime]],
               verbose: bool) -> np.ndarray:
    Nsvmin = 6  # based on GPS only, 20 deg. min elev. at poles

    if Nextra:
        """
        estimated number of satellites per file:
            * RINEX OBS2 files have at least one 80-byte line per time: Nsvmin* ceil(Nobs / 5)

        We open the file and seek because often we're using compressed files
        that have been decompressed in memory only--there is no on-disk
        uncompressed file.
        """
        with opener(fn) as f:
            f.seek(0, io.SEEK_END)
            filesize = f.tell()
            f.seek(0, io.SEEK_SET)  # NEED THIS for io.StringIO input from user!

        Nt = ceil(filesize / 80 / (Nsvmin * Nextra))
        times = np.empty(Nt, dtype=datetime)
    else:  # strict preallocation by double-reading file, OK for < 100 MB files
        t = obstime2(fn, verbose=verbose)  # < 10 ms for 24 hour 15 second cadence
        if tlim is not None:
            times = t[(tlim[0] <= t) & (t <= tlim[1])]
        else:
            times = t

    return times


def obsheader2(f: TextIO,
               useindicators: bool = False,
               meas: Sequence[str] = None) -> Dict[str, Any]:
    """
    End users should use rinexheader()
    """
    if isinstance(f, (str, Path)):
        with opener(f, header=True) as h:
            return obsheader2(h, useindicators, meas)

    f.seek(0)
# %% selection
    if isinstance(meas, str):
        meas = [meas]

    if not meas or not meas[0].strip():
        meas = None

    hdr = rinexinfo(f)
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
                hdr[h] = c[6:].split()
            else:
                hdr[h] += c[6:].split()
        elif h not in hdr:  # Header label
            hdr[h] = c  # string with info
        else:  # concatenate
            hdr[h] += " " + c
# %% useful values
    try:
        hdr['systems'] = hdr['RINEX VERSION / TYPE'][40]
    except KeyError:
        pass

    hdr['Nobs'] = Nobs
    # 5 observations per line (incorporating LLI, SSI)
    hdr['Nl_sv'] = ceil(hdr['Nobs'] / 5)
# %% list with receiver location in x,y,z cartesian ECEF (OPTIONAL)
    try:
        hdr['position'] = [float(j) for j in hdr['APPROX POSITION XYZ'].split()]
        if ecef2geodetic is not None:
            hdr['position_geodetic'] = ecef2geodetic(*hdr['position'])
    except (KeyError, ValueError):
        pass
# %% observation types
    try:
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
    except KeyError:
        pass

    hdr['Nobsused'] = hdr['Nobs']
    if useindicators:
        hdr['Nobsused'] *= 3

# %%
    try:
        hdr['# OF SATELLITES'] = int(hdr['# OF SATELLITES'][:6])
    except (KeyError, ValueError):
        pass
# %% time
    try:
        hdr['t0'] = _timehdr(hdr['TIME OF FIRST OBS'])
    except (KeyError, ValueError):
        pass

    try:
        hdr['t1'] = _timehdr(hdr['TIME OF LAST OBS'])
    except (KeyError, ValueError):
        pass

    try:  # This key is OPTIONAL
        hdr['interval'] = float(hdr['INTERVAL'][:10])
    except (KeyError, ValueError):
        pass

    return hdr


def _getsvind(f: TextIO, ln: str) -> List[str]:
    if len(ln) < 32:
        raise ValueError(f'satellite index line truncated:  {ln}')

    Nsv = int(ln[29:32])  # Number of visible satellites this time %i3
    # get first 12 SV ID's
    sv = _getSVlist(ln, min(12, Nsv), [])

    # any more SVs?
    n = Nsv-12
    while n > 0:
        sv = _getSVlist(f.readline(), min(12, n), sv)
        n -= 12

    if Nsv != len(sv):
        raise ValueError('satellite list read incorrectly')

    return sv


def _getSVlist(ln: str, N: int,
               sv: List[str]) -> List[str]:
    """ parse a line of text from RINEX2 SV list"""
    sv.extend([ln[32+i*3:35+i*3] for i in range(N)])

    return sv


def obstime2(fn: Union[TextIO, Path],
             verbose: bool = False) -> np.ndarray:
    """
    read all times in RINEX2 OBS file
    """
    times = []
    with opener(fn) as f:
        # Capture header info
        hdr = obsheader2(f)

        for ln in f:
            try:
                time_epoch = _timeobs(ln)
            except ValueError:
                continue

            times.append(time_epoch)

            _skip(f, ln, hdr['Nl_sv'])

    times = np.asarray(times)

    check_unique_times(times)

    return times


def _skip(f: TextIO, ln: str,
          Nl_sv: int,
          sv: Sequence[str] = None):
    """
    skip ahead to next time step
    """
    if sv is None:
        sv = _getsvind(f, ln)

    # f.seek(len(sv)*Nl_sv*80, 1)  # not for io.TextIOWrapper ?
    for _ in range(len(sv)*Nl_sv):
        f.readline()


def _timehdr(ln: str) -> datetime:
    """
    handles malformed header dates
    NOTE: must do second=int(float()) due to non-conforming files that don't line up decimal point.
    """

    try:
        second = int(float(ln[30:36]))
    except ValueError:
        second = 0

    if not 0 <= second <= 59:
        second = 0

    try:
        usec = int(float(ln[30:43]) % 1 * 1000000)
    except ValueError:
        usec = 0

    if not 0 <= usec <= 999999:
        usec = 0

    return datetime(year=int(ln[:6]), month=int(ln[6:12]), day=int(ln[12:18]),
                    hour=int(ln[18:24]), minute=int(ln[24:30]),
                    second=second,
                    microsecond=usec)


def _timeobs(ln: str) -> datetime:

    year = int(ln[1:3])
    if year < 80:
        year += 2000
    else:
        year += 1900

    try:
        usec = int(float(ln[16:26]) % 1 * 1000000)
    except ValueError:
        usec = 0

    t = datetime(year=year,
                 month=int(ln[4:6]),
                 day=int(ln[7:9]),
                 hour=int(ln[10:12]),
                 minute=int(ln[13:15]),
                 second=int(ln[16:18]),
                 microsecond=usec)
# %% check if valid time
    eflag = int(ln[28])
    if eflag not in (0, 1, 5, 6):  # EPOCH FLAG
        raise ValueError(f'{t}: epoch flag {eflag}')

    return t


def _skip_header(f: TextIO):
    for ln in f:
        if "END OF HEADER" in ln:
            break


def _fast_alloc(fn: Union[TextIO, Path], Nl_sv: int) -> int:
    """
    prescan first N lines of file to see if it truncates to less than 80 bytes

    Picking N:  N > Nobs+4 or so.
      100 seemed a good start.
    """
    if isinstance(fn, Path):
        assert fn.is_file(), 'need freshly opened file'
    elif isinstance(fn, io.StringIO):
        fn.seek(0)
    else:
        raise TypeError(f'Unknown filetype {type(fn)}')

    with opener(fn) as f:
        _skip_header(f)
# %% find the first line with time (sometimes a blank line or two after header)
        for ln in f:
            try:
                t = _timeobs(ln)
            except ValueError:
                continue

            if isinstance(t, datetime):
                break

        try:
            _getsvind(f, ln)
        except ValueError as e:
            logging.debug(e)
            return 0

        raw = [f.readline() for _ in range(Nl_sv)]

    lens = list(map(len, raw))
    if max(lens) < 79:  # oddly formatted file, no prediction
        return 0

    shorts = sum(l < 79 for l in lens)

    return len(lens) - shorts
