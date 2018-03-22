from __future__ import division  # absolutely needed for Py27 strange behavior
try:
    from pathlib import Path
    Path().expanduser()
except (ImportError,AttributeError):
    from pathlib2 import Path
#
import logging
from math import ceil
import numpy as np
from datetime import datetime
import xarray
from io import BytesIO
from time import time
#
from .rinex2 import _rinexnav2
from .rinex3 import _rinexnav3


#%% Navigation file
def rinexnav(fn, ofn=None):
    fn = Path(fn).expanduser()

    with fn.open('r') as f:
        """verify RINEX version, and that it's NAV"""
        line = f.readline()
        ver = float(line[:9])

    if int(ver) == 2:
        return _rinexnav2(fn,ofn)
    elif int(ver) == 3:
        return _rinexnav3(fn,ofn)
    else:
        raise ValueError('unknown RINEX verion {}  {}'.format(ver,fn))


# %% Observation File
def rinexobs(fn, ofn=None):
    """
    Program overviw:
    1) scan the whole file for the header and other information using scan(lines)
    2) each epoch is read

    rinexobs() returns the data in an xarray.Dataset
    """
    #open file, get header info, possibly speed up reading data with a premade h5 file
    fn = Path(fn).expanduser()
    if fn.suffix=='.nc':
        return xarray.open_dataarray(fn, group='OBS')

    with fn.open('r') as f:
        tic = time()
        data = _scan(f)
        print("finished in {:.2f} seconds".format(time()-tic))


    if ofn:
        ofn = Path(ofn).expanduser()
        print('saving OBS data to',ofn)
        wmode='a' if ofn.is_file() else 'w'

        data.to_netcdf(ofn, group='OBS', mode=wmode)

    return data


def _scan(f):
    """ scan the document for the header info and for the line on
        which each block starts
    """
    header={}
    # Capture header info
    for l in f:
        if "END OF HEADER" in l:
            break

        h = l[60:80]
        c = l[:60]
        if '# / TYPES OF OBSERV' in h:
            c = ' '.join(c.split()[1:]) # drop vestigal count

        if h.strip() not in header: #Header label
            header[h.strip()] = c  # don't strip for fixed-width parsers
            # string with info
        else:
            header[h.strip()] += " " + c
            #concatenate to the existing string


    verRinex = float(header['RINEX VERSION / TYPE'][:9])  # %9.2f
    # list with x,y,z cartesian
    header['APPROX POSITION XYZ'] = [float(j) for j in header['APPROX POSITION XYZ'].split()]
    #observation types
    fields = header['# / TYPES OF OBSERV'].split()
    Nobs = len(fields)

    header['INTERVAL'] = float(header['INTERVAL'][:10])

    data = None
# %% process rest of file
    while True:
        l = f.readline()
        if not l:
            break

        eflag = int(l[28])
        if not eflag in (0,1,5,6): # EPOCH FLAG
             print(eflag)
             continue

        time =  _obstime([l[1:3],  l[4:6], l[7:9],  l[10:12], l[13:15], l[16:26]])
        toffset = float(l[68:80])

        Nsv = int(l[29:32])  # Number of visible satellites this time %i3
        # get first 12 SV ID's
        sv = []
        for i in range(12):
            s = l[32+i*3:35+i*3].strip()
            if not s:
                break
            sv.append(s)

        # any more SVs?
        if Nsv > 12:
            l = f.readline()
            for i in range(Nsv%12):
                sv.append(l[32+i*3:35+i*3])
# %% data processing
        darr = np.empty((Nsv,Nobs*3))
        Nl_sv = ceil(Nobs/5)

        for i,s in enumerate(sv):
            raw = ''
            for _ in range(Nl_sv):
                raw += f.readline()[:80]

            darr[i,:] = np.genfromtxt(BytesIO(raw.encode('ascii')), delimiter=[Nsv,1,1]*Nobs)

        dsf = {}
        for i,k in enumerate(fields):
            dsf[k] = (('time','sv'),np.atleast_2d(darr[:,i*3]))
            if not k in ('S1','S2'): # FIXME which other should be excluded?
                if k in ('L1','L2'):
                    dsf[k+'lli'] = (('time','sv'),np.atleast_2d(darr[:,i*3+1]))
                dsf[k+'ssi'] = (('time','sv'),np.atleast_2d(darr[:,i*3+2]))

        if data is None:
            data = xarray.Dataset(dsf,coords={'time':[time],'sv':sv}, attrs={'toffset':toffset})
        else:
            data = xarray.concat((data,
                                  xarray.Dataset(dsf,coords={'time':[time],'sv':sv}, attrs={'toffset':toffset})),
                                  dim='time')

    data.attrs['filename'] = f.name
    data.attrs['RINEX version'] = verRinex

    return data


def _obstime(fol):
    year = int(fol[0])
    if 80 <= year <=99:
        year+=1900
    elif year<80: #because we might pass in four-digit year
        year+=2000
    return datetime(year=year, month=int(fol[1]), day= int(fol[2]),
                    hour= int(fol[3]), minute=int(fol[4]),
                    second=int(float(fol[5])),
                    microsecond=int(float(fol[5]) % 1 * 100000)
                    )

