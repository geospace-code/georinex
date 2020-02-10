import gzip
import zipfile
from pathlib import Path
from contextlib import contextmanager
import io
import logging
import xarray
from typing.io import TextIO
import typing

try:
    from unlzw3 import unlzw
except ImportError:
    try:
        from unlzw import unlzw
    except ImportError:
        unlzw = None

from .hatanaka import opencrx


@contextmanager
def opener(fn: typing.Union[TextIO, Path],
           header: bool = False) -> TextIO:
    """provides file handle for regular ASCII or gzip files transparently"""
    if isinstance(fn, str):
        fn = Path(fn).expanduser()

    if isinstance(fn, io.StringIO):
        fn.seek(0)
        yield fn
    elif isinstance(fn, Path):
        finf = fn.stat()
        if finf.st_size > 100e6:
            logging.info(f'opening {finf.st_size/1e6} MByte {fn.name}')

        if fn.suffix == '.gz':
            with gzip.open(fn, 'rt') as f:
                version, is_crinex = rinex_version(f.readline(80))
                f.seek(0)

                if is_crinex and not header:
                    f = io.StringIO(opencrx(f))
                yield f
        elif fn.suffix == '.zip':
            with zipfile.ZipFile(fn, 'r') as z:
                flist = z.namelist()
                for rinexfn in flist:
                    with z.open(rinexfn, 'r') as bf:
                        f = io.StringIO(io.TextIOWrapper(bf, encoding='ascii', errors='ignore').read())
                        yield f
        elif fn.suffix == '.Z':
            if unlzw is None:
                raise ImportError('pip install unlzw3')
            with fn.open('rb') as zu:
                with io.StringIO(unlzw(zu.read()).decode('ascii')) as f:
                    yield f
        else:  # assume not compressed (or Hatanaka)
            with fn.open('r', encoding='ascii', errors='ignore') as f:
                version, is_crinex = rinex_version(f.readline(80))
                f.seek(0)

                if is_crinex and not header:
                    f = io.StringIO(opencrx(f))
                yield f
    else:
        raise OSError(f'Unsure what to do with input of type: {type(fn)}')


def rinexinfo(f: typing.Union[Path, TextIO]) -> typing.Dict[str, typing.Any]:
    """verify RINEX version"""

    if isinstance(f, (str, Path)):
        fn = Path(f).expanduser()

        if fn.suffix == '.nc':
            attrs: typing.Dict[str, typing.Any] = {'rinextype': []}
            for g in ('OBS', 'NAV'):
                try:
                    dat = xarray.open_dataset(fn, group=g)
                    attrs['rinextype'].append(g.lower())
                except OSError:
                    continue
                attrs.update(dat.attrs)
            return attrs

        with opener(fn, header=True) as f:
            return rinexinfo(f)

    f.seek(0)

    try:
        line = f.readline(80)  # don't choke on binary files

        if line.startswith('#c'):
            return {'version': 'c',
                    'rinextype': 'sp3'}

        version = rinex_version(line)[0]
        file_type = line[20]
        if int(version) == 2:
            if file_type == 'N':
                system = 'G'
            elif file_type == 'G':
                system = 'R'
            elif file_type == 'E':
                system = 'E'
            else:
                system = line[40]
        else:
            system = line[40]

        if line[20] in ('O', 'C'):
            rinex_type = 'obs'
        elif line[20] == 'N' or 'NAV' in line[20:40]:
            rinex_type = 'nav'
        else:
            rinex_type = line[20]

        info = {'version': version,
                'filetype': file_type,
                'rinextype': rinex_type,
                'systems': system}

    except (TypeError, AttributeError, ValueError, UnicodeDecodeError) as e:
        # keep ValueError for consistent user error handling
        raise ValueError(f'not a known/valid RINEX file.  {e}')

    return info


def rinex_version(s: str) -> typing.Tuple[typing.Union[float, str], bool]:
    """

    Parameters
    ----------

    s : str
       first line of RINEX/CRINEX file

    Results
    -------

    version : float
        RINEX file version

    is_crinex : bool
        is it a Compressed RINEX CRINEX Hatanaka file
    """
    if not isinstance(s, str):
        raise TypeError('need first line of RINEX file as string')
    if len(s) < 2:
        raise ValueError(f'first line of file is corrupted {s}')

    if len(s) >= 80:
        if s[60:80] not in ('RINEX VERSION / TYPE', 'CRINEX VERS   / TYPE'):
            raise ValueError('The first line of the RINEX file header is corrupted.')

    # %% .sp3 file
    if s[0] == '#':
        if s[1] != 'c':
            raise ValueError('Georinex only handles version C of SP3 files.')
        return 'sp3' + s[1], False
    # %% typical RINEX files
    try:
        vers = float(s[:9])  # %9.2f
    except ValueError as err:
        raise ValueError(f'Could not determine file version from {s[:9]}   {err}')

    is_crinex = s[20:40] == 'COMPACT RINEX FORMAT'

    return vers, is_crinex
