import pandas
from typing.io import TextIO
from typing import Sequence, Union
import io
import xarray
from pathlib import Path

from .utils import rinexheader


def get_locations(files: Union[TextIO, Sequence[Path]]) -> pandas.DataFrame:
    """
    retrieve locations of GNSS receivers

    Requires pymap3d.ecef2geodetic
    """
    if isinstance(files, (Path, io.StringIO)):
        files = [files]

    if isinstance(files[0], io.StringIO):
        locs = pandas.DataFrame(index=['0'],
                                columns=['lat', 'lon', 'interval'])
    else:
        locs = pandas.DataFrame(index=[f.name for f in files],
                                columns=['lat', 'lon', 'interval'])

    for f in files:
        if isinstance(f, Path) and f.suffix == '.nc':
            dat = xarray.open_dataset(f, group='OBS')
            hdr = dat.attrs
        else:
            try:
                hdr = rinexheader(f)
            except ValueError:
                continue

        if isinstance(f, Path):
            key = f.name
        else:
            key = '0'

        if 'position_geodetic' not in hdr:
            continue

        locs.loc[key, 'lat'] = hdr['position_geodetic'][0]
        locs.loc[key, 'lon'] = hdr['position_geodetic'][1]
        if 'interval' in hdr and hdr['interval'] is not None:
            locs.loc[key, 'interval'] = hdr['interval']

    locs = locs.loc[locs.loc[:, ['lat', 'lon']].notna().all(axis=1), :]

    return locs
