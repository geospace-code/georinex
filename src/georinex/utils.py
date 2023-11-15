from __future__ import annotations
import typing as T
from pathlib import Path
from datetime import datetime
from dateutil.parser import parse
import io
import xarray

from .rio import rinexinfo, opener
from .obs2 import obstime2, obsheader2
from .obs3 import obstime3, obsheader3
from .nav2 import navtime2, navheader2
from .nav3 import navtime3, navheader3


def globber(path: Path, glob: list[str]) -> list[Path]:
    path = Path(path).expanduser()
    if path.is_file():
        return [path]

    if isinstance(glob, str):
        glob = [glob]

    flist: list[Path] = []
    for g in glob:
        flist += [f for f in path.glob(g) if f.is_file()]

    return flist


def gettime(fn: T.TextIO | Path):
    """
    get times in RINEX 2/3 file
    Note: in header,
        * TIME OF FIRST OBS is mandatory
        * TIME OF LAST OBS is optional

    Parameters
    ----------

    fn : pathlib.Path or io.StringIO
        RINEX file or stream to process

    Returns
    -------

    times : numpy.ndarray of numpy.datetime64
        1-D vector of epochs in file
    """
    info = rinexinfo(fn)

    version = info["version"]
    vers = int(version)
    rtype = info["rinextype"]

    # %% select function
    if rtype == "obs":
        if vers == 2:
            times = obstime2(fn)
        elif vers == 3:
            times = obstime3(fn)
        else:
            raise ValueError(f"Unknown RINEX version {version} {fn}")
    elif rtype == "nav":
        if vers == 2:
            times = navtime2(fn)
        elif vers == 3:
            times = navtime3(fn)
        else:
            raise ValueError(f"Unknown RINEX version {version} {fn}")
    else:
        raise ValueError(f"per-observation time is in NAV, OBS files, not {info}  {fn}")

    return times


def rinexheader(fn: T.TextIO | Path) -> dict[T.Hashable, T.Any]:
    """
    retrieve RINEX 2/3 or CRINEX 1/3 header as unparsed dict()
    """
    if isinstance(fn, (str, Path)):
        fn = Path(fn).expanduser()

    if isinstance(fn, Path) and fn.suffix == ".nc":
        return rinexinfo(fn)
    elif isinstance(fn, Path):
        with opener(fn, header=True) as f:
            return rinexheader(f)
    elif isinstance(fn, io.StringIO):
        fn.seek(0)
    elif isinstance(fn, io.TextIOWrapper):
        pass
    else:
        raise TypeError(f"unknown RINEX filetype {type(fn)}")

    info = rinexinfo(fn)

    hdr: dict[T.Hashable, T.Any]
    if int(info["version"]) in (1, 2):
        if info["rinextype"] == "obs":
            hdr = obsheader2(fn)
        elif info["rinextype"] == "nav":
            hdr = navheader2(fn)
        else:
            raise ValueError(f"Unknown rinex type {info} in {fn}")
    elif int(info["version"]) == 3:
        if info["rinextype"] == "obs":
            hdr = obsheader3(fn)
        elif info["rinextype"] == "nav":
            hdr = navheader3(fn)
        else:
            raise ValueError(f"Unknown rinex type {info} in {fn}")
    else:
        raise ValueError(f"unknown RINEX {info}  {fn}")

    return hdr


def _tlim(tlim: tuple[datetime, datetime] | None = None) -> tuple[datetime, datetime] | None:
    if tlim is None:
        pass
    elif len(tlim) == 2 and isinstance(tlim[0], datetime):
        pass
    elif len(tlim) == 2 and isinstance(tlim[0], str):
        tlim = (parse(tlim[0]), parse(tlim[1]))
    else:
        raise ValueError(f"Not sure what time limits are: {tlim}")

    return tlim


def to_datetime(times: xarray.DataArray):
    """convert to datetime.dattime"""
    if not isinstance(times, xarray.DataArray):
        return times

    t = times.values.astype("datetime64[us]").astype(datetime)

    if not isinstance(t, datetime):
        t = t.squeeze()[()]  # might still be array, but squeezed at least

    return t
