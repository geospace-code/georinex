import xarray
from matplotlib.pyplot import figure
import logging

try:
    from .plots_geo import navtimeseries
except ImportError as e:
    logging.info(e)


def timeseries(data: xarray.Dataset):
    if not isinstance(data, xarray.Dataset):
        return

    if isinstance(data, tuple):
        obs, nav = data
        obstimeseries(obs)
        if navtimeseries is not None:
            navtimeseries(nav)
    elif data.rinextype == 'obs':
        obstimeseries(data)
    elif data.rinextype == 'nav':
        if navtimeseries is not None:
            navtimeseries(data)


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
