import xarray
import pandas
import logging
import numpy as np
from matplotlib.pyplot import figure

try:
    import cartopy
    import cartopy.feature as cpf
except ImportError:
    cartopy = None

try:
    import pymap3d as pm
except ImportError:
    pm = None

from .keplerian import keplerian2ecef


def timeseries(data: xarray.Dataset):
    if not isinstance(data, xarray.Dataset):
        return

    if isinstance(data, tuple):
        obs, nav = data
        obstimeseries(obs)
        navtimeseries(nav)
    elif data.rinextype == 'obs':
        obstimeseries(data)
    elif data.rinextype == 'nav':
        navtimeseries(data)


def receiver_locations(locs: pandas.DataFrame):
    if not isinstance(locs, pandas.DataFrame):
        return

    if cartopy is not None:
        ax = figure().gca(projection=cartopy.crs.PlateCarree())

        ax.add_feature(cpf.LAND)
        ax.add_feature(cpf.OCEAN)
        ax.add_feature(cpf.COASTLINE)
        ax.add_feature(cpf.BORDERS, linestyle=':')
    else:
        ax = figure().gca()

    for name, loc in locs.iterrows():
        if 15 <= loc.interval < 30:
            c = 'g'
        elif 5 <= loc.interval < 15:
            c = 'o'
        elif loc.interval < 5:
            c = 'r'
        else:  # large or undefined interval
            c = 'b'

        if np.isfinite(loc.interval):
            ax.scatter(loc.lon, loc.lat, s=1000*1/loc.interval, c=c, label=name)
        else:
            ax.scatter(loc.lon, loc.lat, c=c, label=name)


def navtimeseries(nav: xarray.Dataset):
    if not isinstance(nav, xarray.Dataset):
        return

    svs = nav.sv.values

    if cartopy is not None:
        ax = figure().gca(projection=cartopy.crs.PlateCarree())

        ax.add_feature(cpf.LAND)
        ax.add_feature(cpf.OCEAN)
        ax.add_feature(cpf.COASTLINE)
        ax.add_feature(cpf.BORDERS, linestyle=':')
    else:
        ax = figure().gca()

    for sv in svs:
        if sv[0] == 'S':
            lat, lon, alt = pm.ecef2geodetic(nav.sel(sv=sv)['X'].dropna(dim='time', how='all'),
                                             nav.sel(sv=sv)['Y'].dropna(
                dim='time', how='all'),
                nav.sel(sv=sv)['Z'].dropna(dim='time', how='all'))

            if ((alt < 35.7e6) | (alt > 35.9e6)).any():
                logging.warning('unrealistic geostationary satellite altitudes')

            if ((lat < -1) | (lat > 1)).any():
                logging.warning('unrealistic geostationary satellite latitudes')

        elif sv[0] == 'R':
            lat, lon, alt = pm.ecef2geodetic(nav.sel(sv=sv)['X'].dropna(dim='time', how='all'),
                                             nav.sel(sv=sv)['Y'].dropna(
                dim='time', how='all'),
                nav.sel(sv=sv)['Z'].dropna(dim='time', how='all'))

            if ((alt < 19.0e6) | (alt > 19.4e6)).any():
                logging.warning('unrealistic GLONASS satellite altitudes')

            if ((lat < -67) | (lat > 67)).any():
                logging.warning('GLONASS inclination ~ 65 degrees')

        elif sv[0] == 'G':
            ecef = keplerian2ecef(nav.sel(sv=sv))
            lat, lon, alt = pm.ecef2geodetic(*ecef)

            if ((alt < 19.4e6) | (alt > 21.0e6)).any():
                logging.warning('unrealistic GPS satellite altitudes')

            if ((lat < -57) | (lat > 57)).any():
                logging.warning('GPS inclination ~ 55 degrees')
        elif sv[0] == 'E':
            ecef = keplerian2ecef(nav.sel(sv=sv))
            lat, lon, alt = pm.ecef2geodetic(*ecef)

            if ((alt < 23e6) | (alt > 24e6)).any():
                logging.warning('unrealistic Galileo satellite altitudes')

            if ((lat < -57) | (lat > 57)).any():
                logging.warning('Galileo inclination ~ 56 degrees')

        else:
            continue

        ax.plot(lon, lat, label=sv)


def obstimeseries(obs: xarray.Dataset):
    if not isinstance(obs, xarray.Dataset):
        return

    for p in ('L1', 'L1C'):
        if p not in obs:
            continue

        dat = obs[p].dropna(how='all', dim='time')

        time = dat.time.values
        if time.size == 0:
            continue

        ax = figure().gca()

        ax.plot(time, dat)

        ax.set_title(obs.filename)
        ax.set_xlabel('time [UTC]')
        ax.set_ylabel(p)
        ax.grid(True)

        ax.legend(dat.sv.values.astype(str), loc='best')
