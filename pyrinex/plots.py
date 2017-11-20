import xarray
from matplotlib.pyplot import figure
#
from pymap3d import eci2geodetic

def plotnav(nav:xarray.DataArray):
    if not isinstance(nav,xarray.DataArray):
        return

    ax = figure().gca()
    if nav.name == 'S':
        # WARNING: This conversion isn't verified.
        lat,lon,alt = eci2geodetic(nav.loc[:,['X','Y','Z']]*1e3,
                                   nav.t.to_pandas().tolist())
        ax.plot(lon,lat)
        ax.set_xlabel('glon [deg]')
        ax.set_ylabel('glat [deg]')

        print('lat lon',lat,lon)
        print('altitude [km]',alt/1e3)


def plotobs(obs:xarray.DataArray):
    if not isinstance(obs,xarray.DataArray):
        return

    ax = figure().gca()

    obs.loc['P1',:,:,'data'].plot(ax=ax)

    ax.set_xlabel('time [UTC]')
    ax.set_ylabel('P1')