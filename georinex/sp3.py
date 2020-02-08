"""
SP3 format:
    https://kb.igs.org/hc/en-us/articles/201096516-IGS-Formats
"""
import xarray
import numpy as np
import logging
from pathlib import Path
from datetime import datetime
import typing

# for NetCDF compression. too high slows down with little space savings.
ENC = {"zlib": True, "complevel": 1, "fletcher32": True}


def load_sp3(fn: Path, outfn: Path) -> xarray.Dataset:
    dat: typing.Dict[str, typing.Any] = {}
    with fn.open("r") as f:
        ln = f.readline()
        assert ln[0] == "#", f"failed to read {fn} line 1"
        dat["t0"] = sp3dt(ln)
        Nepoch = int(ln[32:39])
        dat["coord_sys"] = ln[46:51]
        dat["orbit_type"] = ln[52:55]
        dat["agency"] = ln[56:60]

        f.readline()

        ln = f.readline()
        assert ln[0] == "+", f"failed to read {fn} SV header"
        Nsv = int(ln[4:6])
        svs = get_sv(ln, Nsv)
        if Nsv > 17:
            svs += get_sv(f.readline(), Nsv - 17)
        if Nsv > 34:
            svs += get_sv(f.readline(), Nsv - 34)
        if Nsv > 51:
            svs += get_sv(f.readline(), Nsv - 51)
        if Nsv > 68:
            svs += get_sv(f.readline(), Nsv - 68)
        # let us know if you need these intermediate lines parsed
        for ln in f:
            if ln.startswith("*"):
                break
        if not ln.startswith("*"):  # EOF
            raise ValueError(f"{fn} appears to be badly malformed")
        # the rest of the file is data, punctuated by epoch lines
        ecef = np.empty((Nepoch, Nsv, 3))
        ecef.fill(np.nan)
        clock = np.empty((Nepoch, Nsv, 2))
        clock.fill(np.nan)
        vel = np.empty((Nepoch, Nsv, 3))
        vel.fill(np.nan)
        times = [sp3dt(ln)]
        i = 0
        j = 0

        for ln in f:
            if ln[0] == "*":
                times.append(sp3dt(ln))
                i += 1
                j = 0
                continue

            if ln[0] == "P":
                ecef[i, j, :] = (float(ln[4:18]), float(ln[18:32]), float(ln[32:46]))
                clock[i, j, 0] = float(ln[46:60])
                j += 1
            elif ln[0] == "V":
                vel[i, j - 1, :] = (float(ln[4:18]), float(ln[18:32]), float(ln[32:46]))
                clock[i, j - 1, 1] = float(ln[46:60])
            elif ln[:2] in ("EP", "EV"):
                # let us know if you want these data types
                pass
            elif len(ln) == 0:  # blank line
                pass
            elif ln.startswith("EOF"):
                break
            else:
                logging.info(f"unknown data {ln}")

    # assemble into final xarray.Dataset
    ds = xarray.Dataset(coords={"time": times, "sv": svs, "ECEF": ["x", "y", "z"]})
    ds["position"] = (("time", "sv", "ECEF"), ecef)
    ds["clock"] = (("time", "sv"), clock[:, :, 0])
    if not np.isnan(vel).all():
        ds["velocity"] = (("time", "sv", "ECEF"), vel)
        ds["dclock"] = (("time", "sv"), clock[:, :, 1])

    ds.attrs = dat

    if outfn:
        outfn = Path(outfn).expanduser()
        enc = {k: ENC for k in ds.data_vars}
        ds.to_netcdf(outfn, mode="w", encoding=enc)

    return ds


def sp3dt(ln: str) -> datetime:
    return datetime(
        int(ln[3:7]),
        int(ln[8:10]),
        int(ln[11:13]),
        int(ln[14:16]),
        int(ln[17:19]),
        int(ln[20:22]),
        int(ln[23:28]),
    )


def get_sv(ln: str, Nsv: int) -> typing.List[str]:
    if ln[0] != "+":
        return []
    i0 = 9
    svs = []
    for i in range(min(Nsv, 17)):
        svs.append(ln[i0 + i * 3:(i0 + 3) + i * 3])
    return svs
