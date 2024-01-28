from __future__ import annotations
import typing as T
import gzip
import bz2
import zipfile
from pathlib import Path
from contextlib import contextmanager
import io
import logging

import xarray

try:
    from hatanaka import crx2rnx
except ImportError:
    logging.info("hatanaka crx2rnx not available")
    crx2rnx = None

try:
    from ncompress import decompress as unlzw
except ImportError:
    logging.info("ncompress unlzw not available")
    unlzw = None


@contextmanager
def opener(fn: T.TextIO | Path, header: bool = False) -> T.Iterator[T.TextIO]:
    """provides file handle for regular ASCII or gzip files transparently"""

    if isinstance(fn, str):
        fn = Path(fn).expanduser()

    if isinstance(fn, io.StringIO):
        fn.seek(0)
        yield fn
    elif isinstance(fn, Path):
        # need to have this check for Windows
        if not fn.is_file():
            raise FileNotFoundError(fn)

        finf = fn.stat()
        if finf.st_size > 100e6:
            logging.info(f"opening {finf.st_size / 1e6} MByte {fn.name}")

        # %% get magic number
        """https://en.wikipedia.org/wiki/List_of_file_signatures"""
        with fn.open("rb") as fid:
            magic = fid.read(4)

        suffix = fn.suffix.lower()

        if suffix == ".gz" or magic.startswith(b"\x1f\x8b"):
            with gzip.open(fn, "rt") as f:
                _, is_crinex = rinex_version(first_nonblank_line(f))
                f.seek(0)

                if is_crinex and not header:
                    """
                    gzip compressed CRINEX
                    Conversion to string is necessary because of a quirk where gzip.open()
                    even with 'rt' doesn't decompress until read.
                    """
                    f = io.StringIO(crx2rnx(f.read()))
                yield f
        elif suffix == ".bz2" or magic.startswith(b"\x42\x5a\x68"):
            """
            plain bzip2 files, NOT tar.bz2, which requires f.seek(512)
            """
            with bz2.open(fn, "rt") as f:
                _, is_crinex = rinex_version(first_nonblank_line(f))
                f.seek(0)

                if is_crinex and not header:
                    """
                    bzip2 compressed CRINEX
                    """
                    f = io.StringIO(crx2rnx(f.read()))
                yield f
        elif suffix == ".zip" or magic.startswith(b"\x50\x4b"):
            with zipfile.ZipFile(fn, "r") as z:
                flist = z.namelist()
                for rinexfn in flist:
                    with z.open(rinexfn, "r") as bf:
                        f = io.StringIO(
                            io.TextIOWrapper(bf, encoding="ascii", errors="ignore").read()  # type: ignore
                        )
                        yield f
        elif suffix == ".z" or magic.startswith(b"\x1f\x9d"):
            if unlzw is None:
                raise ImportError("ncompress unlzw not available")

            with fn.open("rb") as zu:
                with io.StringIO(unlzw(zu.read()).decode("ascii")) as f:
                    _, is_crinex = rinex_version(first_nonblank_line(f))
                    f.seek(0)

                    if is_crinex and not header:
                        """
                        LZW compressed CRINEX
                        """
                        f = io.StringIO(crx2rnx(f.read()))
                    yield f
        else:  # assume not compressed (or Hatanaka)
            with fn.open("r", encoding="ascii", errors="ignore") as f:
                _, is_crinex = rinex_version(first_nonblank_line(f))
                f.seek(0)

                if is_crinex and not header:
                    f = io.StringIO(crx2rnx(f))
                yield f
    else:
        raise OSError(f"Unsure what to do with input of type: {type(fn)}")


def first_nonblank_line(f: T.TextIO, max_lines: int = 10) -> str:
    """return first non-blank 80 character line in file

    Parameters
    ----------

    max_lines: int
        maximum number of blank lines
    """

    line = ""
    _i = None
    if max_lines < 1:
        raise ValueError("must read at least one line")

    for _i in range(max_lines):
        line = f.readline(81)
        if line.strip():
            break

    if _i is None or _i == max_lines - 1 or not line:
        raise ValueError(f"could not find first valid header line in {f.name}")

    return line


def rinexinfo(f: T.TextIO | Path) -> dict[T.Hashable, T.Any]:
    """verify RINEX version"""

    if isinstance(f, (str, Path)):
        fn = Path(f).expanduser()

        if fn.suffix == ".nc":
            attrs: dict[T.Hashable, T.Any] = {"rinextype": []}
            for g in ("OBS", "NAV"):
                try:
                    dat = xarray.open_dataset(fn, group=g)
                    attrs["rinextype"].append(g.lower())
                except OSError:
                    continue
                attrs.update(dat.attrs)
            return attrs

        with opener(fn, header=True) as f:
            return rinexinfo(f)

    f.seek(0)

    try:
        line = first_nonblank_line(f)  # don't choke on binary files

        if line.startswith(("#a", "#c", "#d")):
            return {"version": line[1], "rinextype": "sp3"}

        version = rinex_version(line)[0]
        file_type = line[20]
        if int(version) == 2:
            if file_type == "N":
                system = "G"
            elif file_type == "G":
                system = "R"
            elif file_type == "E":
                system = "E"
            else:
                system = line[40]
        else:
            system = line[40]

        if line[20] in ("O", "C"):
            rinex_type = "obs"
        elif line[20] == "N" or "NAV" in line[20:40]:
            rinex_type = "nav"
        else:
            rinex_type = line[20]

        info: dict[T.Hashable, T.Any] = {
            "version": version,
            "filetype": file_type,
            "rinextype": rinex_type,
            "systems": system,
        }

    except (TypeError, AttributeError, ValueError) as e:
        # keep ValueError for consistent user error handling
        raise ValueError(f"not a known/valid RINEX file.  {e}")

    return info


def rinex_version(s: str) -> tuple[float | str, bool]:
    """

    Parameters
    ----------

    s : str
       first line of RINEX/CRINEX/SP3 file

    Results
    -------

    version : float
        RINEX/SP3 file version

    is_crinex : bool
        is it a Compressed RINEX CRINEX Hatanaka file
    """
    if not isinstance(s, str):
        raise TypeError("need first line of RINEX/SP3 file as string")
    if len(s) < 2:
        raise ValueError(f"cannot decode RINEX/SP3 version from line:\n{s}")

    # %% .sp3 file
    if s[0] == "#":
        supported_versions = {"a", "c", "d"}
        if s[1] not in supported_versions:
            raise ValueError(f"SP3 versions of SP3 files currently handled: {supported_versions}")
        return "sp3" + s[1], False

    # %% typical RINEX files
    if len(s) >= 80:
        if s[60:80] not in ("RINEX VERSION / TYPE", "CRINEX VERS   / TYPE"):
            raise ValueError("The first line of the RINEX file header is corrupted.")

    try:
        vers = float(s[:9])  # %9.2f
    except ValueError as err:
        raise ValueError(f"Could not determine file version from {s[:9]}   {err}")

    is_crinex = s[20:40] == "COMPACT RINEX FORMAT"

    return vers, is_crinex
