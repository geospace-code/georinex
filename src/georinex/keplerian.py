"""
GPS Keplerian elements => ECEF
Michael Hirsch, Ph.D.
"""
from datetime import datetime, timedelta
import xarray
import numpy as np
from typing import Tuple


def keplerian2ecef(sv: xarray.DataArray) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    based on:
    https://ascelibrary.org/doi/pdf/10.1061/9780784411506.ap03

    ref:
    https://web.ics.purdue.edu/~ecalais/teaching/gps_geodesy/lab_4.pdf

    http://web.cecs.pdx.edu/~ssp/Reports/2006/Monaghan.pdf
    """

    if 'sv' in sv and sv['sv'] in ('R', 'S'):
        return sv['X'], sv['Y'], sv['Z']

    # sv = sv.dropna(dim='time', how='all')

    GM = 3.986004418e14  # [m^3 s^-2]   Mean anomaly at tk
    omega_e = 7.2921151467e-5  # [rad s^-1]  Mean angular velocity of Earth

    A = sv['sqrtA'].values**2

    n0 = np.sqrt(GM/A**3)  # computed mean motion
#    T = 2*pi / n0  # Satellite orbital period

    n = n0 + sv['DeltaN'].values  # corrected mean motion

    # from GPS Week 0
    if sv.svtype[0] == 'E':
        weeks = sv['GALWeek'].values - 1024
        # TODO: need to add N*4096 for year 2058 and beyond
    elif sv.svtype[0] == 'G':
        weeks = sv['GPSWeek'].values
    else:
        raise ValueError(f'Unknown system type {sv.svtype[0]}')
# %% shaping
    weeks = np.atleast_1d(weeks).astype(float)
    Toe = np.atleast_1d(sv['Toe'].values).astype(float)
    e = sv['Eccentricity'].values

    T0 = [datetime(1980, 1, 6) + timedelta(weeks=week) for week in weeks]

    tk = np.empty(sv['time'].size, dtype=float)

# %% time elapsed since reference epoch
    for i, (t0, t1, t2) in enumerate(zip(T0, sv['time'], Toe)):
        tsv = t1.values.astype('datetime64[us]').astype(datetime)
        toe = timedelta(seconds=t2) + t0  # type: ignore
        tk[i] = (tsv - toe).total_seconds()  # type: ignore
# %% Kepler's eqn of eccentric anomaly
    Mk = sv['M0'].values + n*tk  # Mean Anomaly
    Ek = Mk + e * np.sin(Mk)  # Eccentric anomaly
# %% true anomaly
    nuK = np.arctan2(np.sqrt(1 - e**2) * np.sin(Ek),
                     np.cos(Ek) - e)
# %% latitude
    PhiK = nuK + sv['omega'].values  # argument of latitude
    duk = sv['Cuc'].values * np.cos(2*PhiK) + sv['Cus'].values*np.sin(2*PhiK)  # argument of latitude correction
    uk = PhiK + duk  # corred argument of latitude
# %% inclination (same)
    dik = sv['Cic'].values*np.cos(2*PhiK) + sv['Cis'].values*np.sin(2*PhiK)  # inclination correction
    ik = sv['Io'].values + sv['IDOT'].values*tk + dik  # corrected inclination
# %% radial distance (same)
    drk = sv['Crc'].values * np.cos(2*PhiK) + sv['Crs'].values * np.sin(2*PhiK)  # radial correction
    rk = A * (1 - e * np.cos(Ek)) + drk  # corrected radial distance
# %% right ascension  (same)
    OmegaK = sv['Omega0'].values + (sv['OmegaDot'].values - omega_e)*tk - omega_e*Toe
# %% transform
    Xk1 = rk * np.cos(uk)
    Yk1 = rk * np.sin(uk)

    X = Xk1 * np.cos(OmegaK) - Yk1 * np.sin(OmegaK) * np.cos(ik)

    Y = Xk1*np.sin(OmegaK) + Yk1 * np.cos(OmegaK) * np.cos(ik)

    Z = Yk1*np.sin(ik)

    return X, Y, Z
