import gzip
import zipfile
from pathlib import Path
import subprocess
from contextlib import contextmanager
import io
import os
import logging
import functools
import xarray
from typing.io import TextIO
from typing import Union, Dict, Any, Tuple

try:
    import unlzw
except ImportError:
    unlzw = None


@contextmanager
def opener(fn: Union[TextIO, Path],
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
                    f = io.StringIO(_opencrx(f))
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
                raise ImportError('pip install unlzw')
            with fn.open('rb') as zu:
                with io.StringIO(unlzw.unlzw(zu.read()).decode('ascii')) as f:
                    yield f
        else:  # assume not compressed (or Hatanaka)
            with fn.open('r', encoding='ascii', errors='ignore') as f:
                version, is_crinex = rinex_version(f.readline(80))
                f.seek(0)

                if is_crinex and not header:
                    f = io.StringIO(_opencrx(f))
                yield f
    else:
        raise OSError(f'Unsure what to do with input of type: {type(fn)}')


@functools.lru_cache()
def crxexe() -> str:
    """
    Determines if CRINEX converter is available.
    """
    exe = Path(__file__).resolve().parents[1] / 'rnxcmp' / 'crx2rnx'
    if os.name == 'nt':
        exe = exe.with_suffix('.exe')

    if not exe.is_file():
        return ''

    # crx2rnx -h:  returncode == 1
    ret = subprocess.run([str(exe), '-h'], stderr=subprocess.PIPE,
                         universal_newlines=True)

    if ret.stderr.startswith('Usage'):
        return str(exe)
    else:
        return ''


def _opencrx(f: TextIO) -> str:
    """
    Conversion to string is necessary because of a quirk where gzip.open() even with 'rt' doesn't decompress until read.

    Nbytes is used to read first line.
    """
    exe = crxexe()

    if not exe:
        raise RuntimeError('Hatanka crx2rnx not available. Did you compile it per README?')

    ret = subprocess.check_output([exe, '-'],
                                  input=f.read(),
                                  universal_newlines=True)

    return ret


def rinexinfo(f: Union[Path, TextIO]) -> Dict[str, Any]:
    """verify RINEX version"""

    if isinstance(f, (str, Path)):
        fn = Path(f).expanduser()

        if fn.suffix == '.nc':
            attrs: Dict[str, Any] = {'rinextype': []}
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


def rinex_version(s: str) -> Tuple[float, bool]:
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
        is it a Compacted RINEX file
    """
    if not isinstance(s, str):
        raise TypeError('need first line of RINEX file as string')

    if len(s) >= 80:
        if s[60:80] not in ('RINEX VERSION / TYPE', 'CRINEX VERS   / TYPE'):
            raise ValueError('The first line of the RINEX file header is corrupted.')

    vers = float(s[:9])  # %9.2f
    is_crinex = s[20:40] == 'COMPACT RINEX FORMAT'

    return vers, is_crinex
