import xarray
from matplotlib.pyplot import figure
import cartopy
import cartopy.feature as cpf
#
from pymap3d import ecef2geodetic
from .keplerian import keplerian2ecef


def plotnav(nav: xarray.Dataset):
    if nav is None:
        return

    svs = nav.sv.values

    ax = figure().gca(projection=cartopy.crs.PlateCarree())

    ax.add_feature(cpf.LAND)
    ax.add_feature(cpf.OCEAN)
    ax.add_feature(cpf.COASTLINE)
    ax.add_feature(cpf.BORDERS, linestyle=':')

    for sv in svs:
        if sv[0] == 'S':
            lat, lon, alt = ecef2geodetic(nav.sel(sv=sv)['X'].dropna(dim='time', how='all'),
                                          nav.sel(sv=sv)['Y'].dropna(
                                              dim='time', how='all'),
                                          nav.sel(sv=sv)['Z'].dropna(dim='time', how='all'))
            assert ((35.7e6 < alt) & (alt < 35.9e6)).all(
            ), 'unrealistic geostationary satellite altitudes'
            assert ((-1 < lat) & (lat < 1)
                    ).all(), 'unrealistic geostationary satellite latitudes'
        elif sv[0] == 'R':
            lat, lon, alt = ecef2geodetic(nav.sel(sv=sv)['X'].dropna(dim='time', how='all'),
                                          nav.sel(sv=sv)['Y'].dropna(
                                              dim='time', how='all'),
                                          nav.sel(sv=sv)['Z'].dropna(dim='time', how='all'))
            assert ((19.0e6 < alt) & (alt < 19.4e6)).all(
            ), 'unrealistic GLONASS satellite altitudes'
            assert ((-67 < lat) & (lat < 67)
                    ).all(), 'GPS inclination ~ 65 degrees'
        elif sv[0] == 'G':
            ecef = keplerian2ecef(nav.sel(sv=sv))
            lat, lon, alt = ecef2geodetic(*ecef)
            assert ((19.4e6 < alt) & (alt < 21.0e6)).all(), 'unrealistic GPS satellite altitudes'
            assert ((-57 < lat) & (lat < 57)).all(), 'GPS inclination ~ 55 degrees'
        else:
            continue

        ax.plot(lon, lat, label=sv)


def plotobs(obs: xarray.Dataset):
    if obs is None:
        return

    for p in ('L1', 'L1C'):
        if p not in obs:
            continue

        dat = obs[p].dropna(how='all', dim='time')

        ax = figure().gca()

        ax.plot(dat.time, dat)

        ax.set_title(obs.filename)
        ax.set_xlabel('time [UTC]')
        ax.set_ylabel(p)
        ax.grid(True)

        ax.legend(dat.sv.values.astype(str), loc='best')
