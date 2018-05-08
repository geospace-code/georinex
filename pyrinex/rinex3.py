from pathlib import Path
import numpy as np
from datetime import datetime
from io import BytesIO
import xarray
from typing import Union
from typing.io import TextIO
#
STARTCOL3 = 4 #column where numerical data starts for RINEX 3
"""https://github.com/mvglasow/satstat/wiki/NMEA-IDs"""
SBAS=100 # offset for ID
GLONASS=37
QZSS=192
BEIDOU=0

def _rinexnav3(fn:Path) -> xarray.Dataset:
    """
    Reads RINEX 3.0 NAV files
    Michael Hirsch, Ph.D.
    SciVision, Inc.
    http://www.gage.es/sites/default/files/gLAB/HTML/SBAS_Navigation_Rinex_v3.01.html
    """
    Lf = 19 # string length per field

    fn = Path(fn).expanduser()

    svs = []; epoch=[]; raws=[]

    with fn.open('r') as f:
        """verify RINEX version, and that it's NAV"""
        line = f.readline()
        ver = float(line[:9])
        assert int(ver)==3,'see _rinexnav2() for RINEX 3.0 files'
        assert line[20] == 'N', 'Did not detect Nav file'

        """
        skip header, which has non-constant number of rows
        """
        while True:
            if 'END OF HEADER' in f.readline():
                break
        """
        now read data
        """
        line = f.readline()
        while True:
            sv,time,fields = _newnav(line)
            svs.append(sv)
            epoch.append(time)
# %% get the data as one big long string per SV, unknown # of lines per SV
            raw = line[23:80]  # NOTE: 80, files put data in the last column!

            while True:
                line = f.readline()
                if not line or line[0] != ' ': # new SV
                    break

                raw += line[STARTCOL3:80]
            # one line per SV
            raws.append(raw.replace('D','E'))

            if not line: # EOF
                break
# %% parse
    darr = np.empty((len(raws), len(fields)))

    for i,r in enumerate(raws):
        darr[i,:] = np.genfromtxt(BytesIO(r.encode('ascii')), delimiter=Lf)

    dsf = {f: ('time',d) for (f,d) in zip(fields,darr.T)}
    dsf.update({'sv':('time',svs)})

    nav = xarray.Dataset(dsf,
                          coords={'time':epoch},
                          attrs={'RINEX version':ver,
                                 'RINEX filename':fn.name}
                          )

    return nav


def _newnav(l:str) -> tuple:
    sv = l[:3]

    svtype = sv[0]

    if svtype == 'G':
        """ftp://igs.org/pub/data/format/rinex302.pdf page A-16, A-18"""
        fields = ['SVclockBias','SVclockDrift','SVclockDriftRate',
                  'IODE','Crs','DeltaN','M0',
                  'Cuc','Eccentricity','Cus','sqrtA',
                  'Toe','Cic','omega0','Cis',
                  'Io','Crc','omega','OmegaDot',
                  'IDOT','CodesL2','GPSWeek','L2Pflag',
                  'SVacc','SVhealth','TGD','IODC',
                  'TransTime','FitIntvl']
    elif svtype == 'C':
        raise NotImplementedError('Beidou Compass not yet done')
    elif svtype == 'R':
        raise NotImplementedError('GLONASS Not yet done')
    elif svtype == 'S':
        fields=['SVclockBias','SVRelFreqBias','MsgTxTime',
                'X','dX','dX2','SVhealth',
                'Y','dY','dY2','URA',
                'Z','dZ','dZ2','IODN']
    elif svtype == 'J':
        raise NotImplementedError('QZSS not yet done')
    elif svtype == 'E':
        raise NotImplementedError('Galileo not yet done')
    else:
        raise ValueError('Unknown SV type {}'.format(sv[0]))


    year = int(l[4:8]) # I4

    time = datetime(year = year,
                  month   =int(l[9:11]),
                  day     =int(l[12:14]),
                  hour    =int(l[15:17]),
                  minute  =int(l[18:20]),
                  second  =int(l[21:23]))

    return sv, time, fields


def _scan3(fn:Path, use:Union[str,list,tuple], verbose:bool=False) -> xarray.Dataset:
    """
    procss RINEX OBS data
    """

    with fn.open('r') as f:
        fields, header, Fmax = _getObsTypes(f, use)


        data = None
    # %% process rest of file
        while True:
            l = f.readline()
            if not l:
                break

            assert l[0] == '>'  # pg. A13

            time = datetime(int(l[2:6]), int(l[7:9]), int(l[10:12]),
                            hour=int(l[13:15]), minute=int(l[16:18]), second=int(l[19:21]),
                            microsecond=int(l[22:29])*1000000)
            if verbose:
                print(time,'\r',end="")
# %% get SV indices
            Nsv = int(l[33:35])  # Number of visible satellites this time %i3  pg. A13

            sv = []
            raw = ''
            for i in range(Nsv):
                l = f.readline()
                k = l[:3]
                sv.append(k)
                raw += l[3:]

            darr = np.genfromtxt(BytesIO(raw.encode('ascii')), delimiter=(14,1,1)*Fmax)
# %% Tselect one, few, or all satellites
            i = [i for i,s in enumerate(sv) if s[0] in use]
            garr = darr[i,:]
            gsv = np.array(sv)[i]
# %% assign data for each time step
            dsf = {}
            for i,k in enumerate(fields):
                dsf[k] = (('time','sv'), np.atleast_2d(garr[:,i*3]))
                if k.startswith('L1') or k.startswith('L2'):
                   dsf[k+'lli'] = (('time','sv'), np.atleast_2d(garr[:,i*3+1]))
                dsf[k+'ssi'] = (('time','sv'), np.atleast_2d(garr[:,i*3+2]))

            if verbose:
                print(time,'\r',end='')

            if data is None:
                data = xarray.Dataset(dsf,coords={'time':[time],'sv':gsv})#, attrs={'toffset':toffset})
            else:
                data = xarray.concat((data,
                                      xarray.Dataset(dsf,coords={'time':[time],'sv':gsv})),#, attrs={'toffset':toffset})),
                                    dim='time')

    data.attrs['filename'] = f.name

    return data


def _getObsTypes(f:TextIO, use:Union[str,list,tuple]) -> tuple:
    """ get RINEX 3 OBS types, for each system type"""
    header={}
    fields={}
    Fmax = 0
    # Capture header info
    for l in f:
        if "END OF HEADER" in l:
            break

        h = l[60:80]
        c = l[:60]
        if 'SYS / # / OBS TYPES' in h:
            k = c[0]
            fields[k] = c[6:60].split()
            N = int(c[3:6])
            Fmax = max(N,Fmax)

            n = N-13
            while n > 0: # Rinex 3.03, pg. A6, A7
                l = f.readline()
                assert 'SYS / # / OBS TYPES' in l[60:]
                fields[k] += l[6:60].split()
                n -= 13

            assert len(fields[k]) == N

            continue

        if h.strip() not in header: #Header label
            header[h.strip()] = c  # don't strip for fixed-width parsers
            # string with info
        else: # concatenate to the existing string
            header[h.strip()] += " " + c
# %% sanity check for Mandatory RINEX 3 headers
    for h in ('APPROX POSITION XYZ',):
        if not h in header:
            raise IOError('Mandatory RINEX 3 headers are missing from file, is it a valid RINEX 3 file?')

    # list with x,y,z cartesian
    header['APPROX POSITION XYZ'] = [float(j) for j in header['APPROX POSITION XYZ'].split()]
# %% select specific satellite systems only (optional)
    if isinstance(use,str):
        fields = fields[use]
    elif isinstance(use,(tuple,list,np.ndarray)):
        fields = [fields[u] for u in use]

    return fields, header, Fmax
