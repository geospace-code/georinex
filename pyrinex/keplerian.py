"""
GPS Keplerian elements => ECEF
Michael Hirsch, Ph.D.
"""
from datetime import datetime, timedelta
import xarray
import numpy as np
from typing import Union

def keplerian2ecef(sv:Union[dict,xarray.DataArray]):
    """
    based on:
    https://ascelibrary.org/doi/pdf/10.1061/9780784411506.ap03
    """

    GM = 3.986005e14  # [m^3 s^-2]
    omega_e = 7.292115e-5  # [rad s^-1]
    pi = 3.1415926535898 # definition

    A = sv['sqrtA']**2

    n0 = np.sqrt(GM/A**3)  # computed mean motion
    T = 2*pi / n0  # Satellite orbital period

    n = n0 + sv['DeltaN'] # corrected mean motion

    t0 = datetime(1980,1,6) + timedelta(weeks=sv['GPSWeek'][0].astype(int).item())  # from GPS Week 0

    tk = np.empty(sv['time'].size,dtype=float)
    # FIXME: so ugly...
    for i,(t1,t2) in enumerate(zip(sv['time'],sv['Toe'])):
        tk[i] = (datetime.utcfromtimestamp(t1.item()/1e9) - (timedelta(seconds=t2.values.astype(int).item()) + t0)).total_seconds()    # time elapsed since reference epoch

    Mk = sv['M0'] + n*tk  # Mean Anomaly
    Ek = Mk + sv['Eccentricity'] * np.sin(Mk)  # FIXME: ok?

    nuK = np.arccos( (np.cos(Ek) - sv['Eccentricity']) / (1-sv['Eccentricity']*np.cos(Ek)))

    PhiK = nuK + sv['omega']
    dik = sv['Cic']*np.cos(2*PhiK) + sv['Cis']*np.sin(2*PhiK)

    ik = sv['Io'] + sv['IDOT']*tk + dik

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