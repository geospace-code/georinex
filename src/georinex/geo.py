from __future__ import annotations
import pandas
import io
import xarray
import typing as T
from pathlib import Path

from .utils import rinexheader


def get_locations(files: list[Path]) -> pandas.DataFrame:
    """
    retrieve locations of GNSS receivers

    Requires pymap3d.ecef2geodetic
    """
    if isinstance(files, (Path, io.StringIO)):
        files = [files]

    if isinstance(files[0], io.StringIO):
        locs = pandas.DataFrame(index=["0"], columns=["lat", "lon", "interval"])
    elif isinstance(files[0], Path):
        locs = pandas.DataFrame(
            index=[file.name for file in files], columns=["lat", "lon", "interval"]
        )
    else:
        raise TypeError("Expecting pathlib.Path")

    hdr: dict[T.Hashable, T.Any]
    for file in files:
        if isinstance(file, Path) and file.suffix == ".nc":
            dat = xarray.open_dataset(file, group="OBS")
            hdr = dat.attrs
        else:
            try:
                hdr = rinexheader(file)
            except ValueError:
                continue

        if isinstance(file, Path):
            key = file.name
        else:
            key = "0"

        if "position_geodetic" not in hdr:
            continue

        locs.loc[key, "lat"] = hdr["position_geodetic"][0]
        locs.loc[key, "lon"] = hdr["position_geodetic"][1]
        if "interval" in hdr and hdr["interval"] is not None:
            locs.loc[key, "interval"] = hdr["interval"]

    locs = locs.loc[locs.loc[:, ["lat", "lon"]].notna().all(axis=1), :]

    return locs
