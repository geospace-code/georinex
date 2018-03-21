import xarray
from matplotlib.pyplot import figure
#
from pymap3d import eci2geodetic

def plotnav(nav:xarray.Dataset):

    if not 'X' in nav:
        return

    ax = figure().gca()
    # WARNING: This conversion isn't verified.
    lat,lon,alt = eci2geodetic(nav[['X','Y','Z']]*1e3,
                               nav.time)
    ax.plot(lon,lat)
    ax.set_xlabel('glon [deg]')
    ax.set_ylabel('glat [deg]')

    print('lat lon',lat,lon)
    print('altitude [km]',alt/1e3)


def plotobs(obs:xarray.DataArray):

    ax = figure().gca()

    obs.loc['P1',:,:,'data'].plot(ax=ax)

    ax.set_xlabel('time [UTC]')
    ax.set_ylabel('P1')