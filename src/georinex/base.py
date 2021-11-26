from __future__ import annotations
import typing as T
from pathlib import Path
import xarray
from datetime import datetime, timedelta
import logging

from .rio import rinexinfo
from .obs2 import rinexobs2
from .obs3 import rinexobs3
from .nav2 import rinexnav2
from .nav3 import rinexnav3
from .sp3 import load_sp3
from .utils import _tlim

# for NetCDF compression. too high slows down with little space savings.
ENC = {"zlib": True, "complevel": 1, "fletcher32": True}


def load(
    rinexfn: T.TextIO | str | Path,
    out: Path = None,
    use: list[str] = None,
    tlim: tuple[datetime, datetime] = None,
    useindicators: bool = False,
    meas: list[str] = None,
    verbose: bool = False,
    *,
    overwrite: bool = False,
    fast: bool = True,
    interval: float | int | timedelta = None,
) -> xarray.Dataset | dict[str, xarray.Dataset]:
    """
    Reads OBS, NAV in RINEX 2.x and 3.x

    Files / StringIO input may be plain ASCII text or compressed (including Hatanaka)
    """
    if verbose:
        logging.basicConfig(level=logging.INFO)

    if isinstance(rinexfn, (str, Path)):
        rinexfn = Path(rinexfn).expanduser()
    # %% determine if/where to write NetCDF4/HDF5 output
    outfn = None
    if out:
        out = Path(out).expanduser()
        if out.is_dir():
            outfn = out / (
                rinexfn.name + ".nc"
            )  # not with_suffix to keep unique RINEX 2 filenames
        elif out.suffix == ".nc":
            outfn = out
        else:
            raise ValueError(f"not sure what output is wanted: {out}")
    # %% main program
    if tlim is not None:
        if len(tlim) != 2:
            raise ValueError("time bounds are specified as start stop")
        if tlim[1] < tlim[0]:
            raise ValueError("stop time must be after start time")

    info = rinexinfo(rinexfn)

    if info["rinextype"] == "nav":
        return rinexnav(rinexfn, outfn, use=use, tlim=tlim, overwrite=overwrite)
    elif info["rinextype"] == "obs":
        return rinexobs(
            rinexfn,
            outfn,
            use=use,
            tlim=tlim,
            useindicators=useindicators,
            meas=meas,
            verbose=verbose,
            overwrite=overwrite,
            fast=fast,
            interval=interval,
        )

    assert isinstance(rinexfn, Path)

    if info["rinextype"] == "sp3":
        return load_sp3(rinexfn, outfn)
    elif rinexfn.suffix == ".nc":
        # outfn not used here, because we already have the converted file!
        try:
            nav = rinexnav(rinexfn)
        except LookupError:
            nav = None

        try:
            obs = rinexobs(rinexfn)
        except LookupError:
            obs = None

        if nav is not None and obs is not None:
            return {"nav": nav, "obs": rinexobs(rinexfn)}
        elif nav is not None:
            return nav
        elif obs is not None:
            return obs
        else:
            raise ValueError(f"No data of known format found in {rinexfn}")
    else:
        raise ValueError(f"What kind of RINEX file is: {rinexfn}")


def batch_convert(
    path: Path,
    glob: str,
    out: Path,
    use: list[str] = None,
    tlim: tuple[datetime, datetime] = None,
    useindicators: bool = False,
    meas: list[str] = None,
    verbose: bool = False,
    *,
    fast: bool = True,
):

    path = Path(path).expanduser()

    flist = (f for f in path.glob(glob) if f.is_file())

    for fn in flist:
        try:
            load(
                fn,
                out,
                use=use,
                tlim=tlim,
                useindicators=useindicators,
                meas=meas,
                verbose=verbose,
                fast=fast,
            )
        except ValueError as e:
            logging.error(f"{fn.name}: {e}")


def rinexnav(
    fn: T.TextIO | str | Path,
    outfn: Path = None,
    use: list[str] = None,
    group: str = "NAV",
    tlim: tuple[datetime, datetime] = None,
    *,
    overwrite: bool = False,
) -> xarray.Dataset:
    """Read RINEX 2 or 3  NAV files"""

    if isinstance(fn, (str, Path)):
        fn = Path(fn).expanduser()

        if fn.suffix == ".nc":
            try:
                return xarray.open_dataset(fn, group=group)
            except OSError as e:
                raise LookupError(f"Group {group} not found in {fn}    {e}")

    tlim = _tlim(tlim)

    info = rinexinfo(fn)
    if int(info["version"]) == 2:
        nav = rinexnav2(fn, tlim=tlim)
    elif int(info["version"]) == 3:
        nav = rinexnav3(fn, use=use, tlim=tlim)
    else:
        raise LookupError(f"unknown RINEX  {info}  {fn}")

    # %% optional output write
    if outfn:
        outfn = Path(outfn).expanduser()
        wmode = _groupexists(outfn, group, overwrite)

        enc = {k: ENC for k in nav.data_vars}
        nav.to_netcdf(outfn, group=group, mode=wmode, encoding=enc)

    return nav


# %% Observation File


def rinexobs(
    fn: T.TextIO | Path,
    outfn: Path = None,
    use: list[str] = None,
    group: str = "OBS",
    tlim: tuple[datetime, datetime] = None,
    useindicators: bool = False,
    meas: list[str] = None,
    verbose: bool = False,
    *,
    overwrite: bool = False,
    fast: bool = True,
    interval: float | int | timedelta = None,
) -> xarray.Dataset:
    """
    Read RINEX 2.x and 3.x OBS files in ASCII or GZIP (or Hatanaka)
    """

    if isinstance(fn, (str, Path)):
        fn = Path(fn).expanduser()
        # %% NetCDF4
        if fn.suffix == ".nc":
            try:
                return xarray.open_dataset(fn, group=group)
            except OSError as e:
                raise LookupError(f"Group {group} not found in {fn}   {e}")

    tlim = _tlim(tlim)
    # %% version selection
    info = rinexinfo(fn)

    if int(info["version"]) in (1, 2):
        obs = rinexobs2(
            fn,
            use,
            tlim=tlim,
            useindicators=useindicators,
            meas=meas,
            verbose=verbose,
            fast=fast,
            interval=interval,
        )
    elif int(info["version"]) == 3:
        obs = rinexobs3(
            fn,
            use,
            tlim=tlim,
            useindicators=useindicators,
            meas=meas,
            verbose=verbose,
            fast=fast,
            interval=interval,
        )
    else:
        raise ValueError(f"unknown RINEX {info}  {fn}")

    # %% optional output write
    if outfn:
        outfn = Path(outfn).expanduser()
        wmode = _groupexists(outfn, group, overwrite)
        enc = {k: ENC for k in obs.data_vars}

        # Pandas >= 0.25.0 requires this, regardless of xarray version
        if obs.time.dtype != "datetime64[ns]":
            obs["time"] = obs.time.astype("datetime64[ns]")
        obs.to_netcdf(outfn, group=group, mode=wmode, encoding=enc)

    return obs


def _groupexists(fn: Path, group: str, overwrite: bool) -> str:
    print(f"saving {group}:", fn)
    if overwrite or not fn.is_file():
        return "w"

    # be sure there isn't already NAV in it
    try:
        xarray.open_dataset(fn, group=group)
        raise ValueError(f"{group} already in {fn}")
    except OSError:
        pass

    return "a"
