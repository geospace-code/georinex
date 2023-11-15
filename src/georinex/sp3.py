"""
SP3 format:
    https://kb.igs.org/hc/en-us/articles/201096516-IGS-Formats
"""

from __future__ import annotations
import typing as T
import xarray
import numpy as np
import logging
from pathlib import Path
from datetime import datetime, timedelta

from .rio import first_nonblank_line, opener

# for NetCDF compression. too high slows down with little space savings.
ENC = {"zlib": True, "complevel": 1, "fletcher32": True}

__all__ = ["load_sp3"]


def load_sp3(fn: Path, outfn: Path | None) -> xarray.Dataset:
    """
    The basic format is a position and clock record;
    a second, optional, record contains velocities and clock rates-of-change.

    http://epncb.oma.be/ftp/data/format/sp3_docu.txt  (sp3a)
    """

    dat: dict[T.Hashable, T.Any] = {}

    with opener(fn) as f:
        ln = first_nonblank_line(f)
        assert ln[0] == "#", f"failed to read {fn} line 1"
        # sp3_version = ln[1]
        t0 = sp3dt(ln)
        # Nepoch != number of time steps, at least for some files
        dat["Nepoch"] = int(ln[32:39])
        dat["coord_sys"] = ln[46:51]
        dat["orbit_type"] = ln[52:55]
        dat["agency"] = ln[56:60]

        f.readline()
        ln = f.readline()
        assert ln[0] == "+", f"failed to read {fn} SV header"
        # version c : Nsv <= 85, int(ln[4:6])
        # version d : Nsv <= 999, int(len[3:6])
        # (see ftp://igs.org/pub/data/format/sp3d.pdf)
        # So this should work for both versions
        Nsv = int(ln[3:6])
        svs = get_sv(ln, Nsv)
        unread_sv = Nsv - 17
        while unread_sv > 0:
            svs += get_sv(f.readline(), unread_sv)
            unread_sv -= 17
        # let us know if you need these intermediate lines parsed
        for ln in f:
            if ln.startswith("*"):
                break
        if not ln.startswith("*"):  # EOF
            raise ValueError(f"{fn} appears to be badly malformed")
        # the rest of the file is data, punctuated by epoch lines
        ecefs = []
        clocks = []
        vels = []
        ecef = np.empty((Nsv, 3))
        clock = np.empty((Nsv, 2))
        vel = np.empty((Nsv, 3))
        i = 0

        times = [sp3dt(ln)]

        for ln in f:
            if ln[0] == "*":
                times.append(sp3dt(ln))
                ecefs.append(ecef)
                clocks.append(clock)
                vels.append(vel)

                ecef = np.empty((Nsv, 3))
                clock = np.empty((Nsv, 2))  # clock and clock rate-of-change

                vel = np.empty((Nsv, 3))
                vel.fill(np.nan)  # may not always have velocity

                i = 0
                continue

            if ln[0] == "P":
                ecef[i, :] = (float(ln[4:18]), float(ln[18:32]), float(ln[32:46]))
                clock[i, 0] = float(ln[46:60])
                i += 1
            elif ln[0] == "V":
                vel[i - 1, :] = (float(ln[4:18]), float(ln[18:32]), float(ln[32:46]))
                clock[i - 1, 1] = float(ln[46:60])
            elif ln.startswith(("EP", "EV")):
                # let us know if you want these data types
                pass
            elif len(ln) == 0:  # blank line
                pass
            elif len(ln) >= 4 and ln[3] == "*":  # sp3a no data
                continue
            elif ln.startswith("EOF"):
                break
            else:
                logging.info(f"unknown data {ln}")

    # assemble the last time step
    ecefs.append(ecef)
    clocks.append(clock)
    vels.append(vel)

    aclock = np.asarray(clocks)

    # assemble into final xarray.Dataset
    ds = xarray.Dataset(coords={"time": times, "sv": svs, "ECEF": ["x", "y", "z"]})
    ds["position"] = (("time", "sv", "ECEF"), ecefs)
    ds["clock"] = (("time", "sv"), aclock[:, :, 0])

    ds["velocity"] = (("time", "sv", "ECEF"), vels)
    ds["dclock"] = (("time", "sv"), aclock[:, :, 1])

    ds["t0"] = t0

    ds.attrs = dat

    if outfn:
        outfn = Path(outfn).expanduser()
        enc = {k: ENC for k in ds.data_vars}
        ds.to_netcdf(outfn, mode="w", encoding=enc, format="NETCDF4")

    return ds


def sp3dt(ln: str) -> datetime:
    """
    some receivers such as ESA Swarm return seconds=60, so let's patch this.
    """

    dt = []

    hour = int(ln[14:16])
    minute = int(ln[17:19])
    second = int(ln[20:22])

    if second == 60:
        dt.append(timedelta(minutes=1))
        second = 0

    if minute == 60:
        dt.append(timedelta(hours=1))
        minute = 0

    if hour == 24:
        dt.append(timedelta(days=1))
        hour = 0

    time = datetime(
        year=int(ln[3:7]),
        month=int(ln[8:10]),
        day=int(ln[11:13]),
        hour=hour,
        minute=minute,
        second=second,
        microsecond=int(ln[23:29]),
    )

    for t in dt:
        time += t

    return time


def get_sv(ln: str, Nsv: int) -> list[str]:
    if ln[0] != "+":
        return []
    i0 = 9
    svs = []
    for i in range(min(Nsv, 17)):
        svs.append(ln[i0 + i * 3 : (i0 + 3) + i * 3].replace(" ", ""))

    return svs
