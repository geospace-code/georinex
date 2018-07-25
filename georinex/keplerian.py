"""
GPS Keplerian elements => ECEF
Michael Hirsch, Ph.D.
"""
from datetime import datetime, timedelta
import xarray
import numpy as np


def keplerian2ecef(sv: xarray.DataArray) -> tuple:
    """
    based on:
    https://ascelibrary.org/doi/pdf/10.1061/9780784411506.ap03
    """

    if 'sv' in sv and sv['sv'] in ('R', 'S'):
        return sv['X'], sv['Y'], sv['Z']

    sv = sv.dropna(dim='time', how='all')

    GM = 3.986005e14  # [m^3 s^-2]
    omega_e = 7.292115e-5  # [rad s^-1]
#    pi = 3.1415926535898  # definition

    A = sv['sqrtA']**2

    n0 = np.sqrt(GM/A**3)  # computed mean motion
#    T = 2*pi / n0  # Satellite orbital period

    n = n0 + sv['DeltaN']  # corrected mean motion

    # from GPS Week 0
    t0 = datetime(1980, 1, 6) + timedelta(weeks=sv['GPSWeek'][0].astype(int).item())

    tk = np.empty(sv['time'].size, dtype=float)

    # FIXME: so ugly...
    # time elapsed since reference epoch
    # seems to be a bug in MyPy, this line computes "correctly"

    for i, (t1, t2) in enumerate(zip(sv['time'], sv['Toe'])):
        tsv = datetime.utcfromtimestamp(t1.item()/1e9)
        toe = timedelta(seconds=t2.values.astype(int).item()) + t0  # type: ignore  # noqa
        tk[i] = (tsv - toe).total_seconds()  # type: ignore  # noqa

    Mk = sv['M0'] + n*tk  # Mean Anomaly
    Ek = Mk + sv['Eccentricity'] * np.sin(Mk)  # FIXME: ok?

    nuK = 2 * np.arctan2(np.sqrt(1 + sv['Eccentricity']) *
                         np.sin(Ek/2), np.sqrt(1-sv['Eccentricity']) * np.cos(Ek/2))

    PhiK = nuK + sv['omega']
    dik = sv['Cic']*np.cos(2*PhiK) + sv['Cis']*np.sin(2*PhiK)

    ik = sv['Io'] + sv['IDOT']*tk + dik  # corrected inclination

    duk = sv['Cuc'] * np.cos(2*PhiK) + sv['Cus']*np.sin(2*PhiK)
    uk = PhiK + duk

    drk = sv['Crc']*np.cos(2*PhiK) + sv['Crs']*np.sin(2*PhiK)
    rk = A*(1-sv['Eccentricity']*np.cos(Ek)) + drk
    Xk1 = rk * np.cos(uk)

    Yk1 = rk*np.sin(uk)

    OmegaK = sv['Omega0'] + (sv['OmegaDot'] - omega_e)*tk - omega_e*sv['Toe']

    X = Xk1 * np.cos(OmegaK) - Yk1 * np.sin(OmegaK) * np.cos(ik)

    Y = Xk1*np.sin(OmegaK) + Yk1 * np.cos(OmegaK) * np.cos(ik)

    Z = Yk1*np.sin(ik)

    return X, Y, Z
