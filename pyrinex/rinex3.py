from pathlib import Path
import numpy as np
from datetime import datetime
from io import BytesIO
import xarray
import logging
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

    svs = []; raws=[]; fields = {}; t = []

    with fn.open('r') as f:
        """verify RINEX version, and that it's NAV"""
        line = f.readline()
        ver = float(line[:9])
        assert int(ver)==3,'see _rinexnav2() for RINEX 3.0 files'
        assert line[20] == 'N', 'Did not detect Nav file'
#        svtype=line[40]
# %% skip header, which has non-constant number of rows
        for line in f:
            if 'END OF HEADER' in line:
                break
# %% read data
        # these while True are necessary to make EOF work right. not for line in f!
        line = f.readline()
        svtypes=[line[0]]
        while True:
            sv,time,field = _newnav(line)
            t.append(time)

            if sv[0] != svtypes[-1]:
                svtypes.append(sv[0])
            else:
                fields[svtypes[-1]] = field

            svs.append(sv)
# %% get the data as one big long string per SV, unknown # of lines per SV
            raw = line[23:80]  # NOTE: 80, files put data in the last column!

            while True:
                line = f.readline().rstrip()
                if not line or line[0] != ' ': # new SV
                    break

                raw += line[STARTCOL3:80]
            # one line per SV
            raws.append(raw.replace('D','E'))

            if not line: # EOF
                break
# %% parse
    t = np.array([np.datetime64(T,'ns') for T in t])
    nav = None
    svu = sorted(set(svs))

    for sv in svu:
        svi = [i for i,s in enumerate(svs) if s==sv]

        tu = list(set(t[svi]))
        if len(tu) != len(t[svi]):
            logging.warning('duplicate times detected, skipping SV {}'.format(sv))
            continue

        darr = np.empty((len(svi), len(fields[sv[0]])))

        for j,i in enumerate(svi):
            darr[j,:] = np.genfromtxt(BytesIO(raws[i].encode('ascii')), delimiter=Lf)

        dsf = {}
        for (f,d) in zip(fields[sv[0]], darr.T):
            if sv[0] in ('R','S') and f in ('X','dX','dX2',
                                            'Y','dY','dY2',
                                            'Z','dZ','dZ2'):
                d *= 1000 # km => m

            dsf[f] = (('time','sv'), d[:,None])



        if nav is None:
            nav = xarray.Dataset(dsf, coords={'time':t[svi],'sv':[sv]})
        else:
            nav = xarray.merge((nav,
                                xarray.Dataset(dsf, coords={'time':t[svi],'sv':[sv]})))


    nav.attrs['version'] = ver
    nav.attrs['filename'] = fn.name
    nav.attrs['svtype'] = svtypes

    return nav


def _newnav(l:str) -> tuple:
    sv = l[:3]

    svtype = sv[0]

    if svtype == 'G':
        """
        ftp://igs.org/pub/data/format/rinex303.pdf page A-23 - A-24
        """
        fields = ['SVclockBias','SVclockDrift','SVclockDriftRate',
                  'IODE','Crs','DeltaN','M0',
                  'Cuc','Eccentricity','Cus','sqrtA',
                  'Toe','Cic','Omega0','Cis',
                  'Io','Crc','omega','OmegaDot',
                  'IDOT','CodesL2','GPSWeek','L2Pflag',
                  'SVacc','health','TGD','IODC',
                  'TransTime','FitIntvl']
    elif svtype == 'C': # pg A-33  Beidou Compass BDT
        fields = ['SVclockBias','SVclockDrift','SVclockDriftRate',
                  'AODE','Crs','DeltaN','M0',
                  'Cuc','Eccentricity','Cus','sqrtA',
                  'Toe','Cic','Omega0','Cis',
                  'Io','Crc','omega','OmegaDot',
                  'IDOT','BDTWeek',
                  'SVacc','SatH1','TGD1','TGD2',
                  'TransTime','AODC']
    elif svtype == 'R': # pg. A-29   GLONASS
        fields = ['SVclockBias','SVrelFreqBias','MessageFrameTime',
                  'X','dX','dX2','health',
                  'Y','dY','dY2','FreqNum',
                  'Z','dZ','dZ2','AgeOpInfo']
    elif svtype == 'S': # pg. A-35 SBAS
        fields=['SVclockBias','SVrelFreqBias','MessageFrameTime',
                'X','dX','dX2','health',
                'Y','dY','dY2','URA',
                'Z','dZ','dZ2','IODN']
    elif svtype == 'J':  # pg. A-31  QZSS
        fields = ['SVclockBias','SVclockDrift','SVclockDriftRate',
                  'IODE','Crs','DeltaN','M0',
                  'Cuc','Eccentricity','Cus','sqrtA',
                  'Toe','Cic','Omega0','Cis',
                  'Io','Crc','omega','OmegaDot',
                  'IDOT','CodesL2','GPSWeek','L2Pflag',
                  'SVacc','health','TGD','IODC',
                  'TransTime','FitIntvl']
    elif svtype == 'E':
        fields = ['SVclockBias','SVclockDrift','SVclockDriftRate',
                  'IODnav','Crs','DeltaN','M0',
                  'Cuc','Eccentricity','Cus','sqrtA',
                  'Toe','Cic','Omega0','Cis',
                  'Io','Crc','omega','OmegaDot',
                  'IDOT','DataSrc','GALWeek',
                  'SISA','health','BGDe5a','BGDe5b',
                  'TransTime']
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

# %% OBS

def _scan3(fn:Path, use:Union[str,list,tuple], verbose:bool=False) -> xarray.Dataset:
    """
    procss RINEX OBS data
    """

    if (not use or not use[0].strip() or
      isinstance(use,str) and use.lower() in ('m','all') or
      isinstance(use,(tuple,list,np.ndarray)) and use[0].lower() in ('m','all')):

      use = None

    with fn.open('r') as f:
        l = f.readline()
        version = float(l[:9]) # yes :9
        fields, header, Fmax = _getObsTypes(f, use)


        data = None
    # %% process rest of file
        while True:
            l = f.readline().rstrip()
            if not l:
                break

            assert l[0] == '>'  # pg. A13
            """
            Python >=merge 3.7 supports nanoseconds.  https://www.python.org/dev/peps/pep-0564/
            Python < 3.7 supports microseconds.
            """
            time = datetime(int(l[2:6]), int(l[7:9]), int(l[10:12]),
                            hour=int(l[13:15]), minute=int(l[16:18]), second=int(l[19:21]),
                            microsecond=int(float(l[19:29]) % 1 * 1000000))
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
# %% assign data for each time step
            for sk in fields: # for each satellite system type (G,R,S, etc.)
                i = [i for i,s in enumerate(sv) if s[0] in sk]

                garr = darr[i,:]
                gsv = np.array(sv)[i]

                dsf = {}
                for i,k in enumerate(fields[sk]):
                    dsf[k] = (('time','sv'), np.atleast_2d(garr[:,i*3]))

                    if k.startswith('L1') or k.startswith('L2'):
                       dsf[k+'lli'] = (('time','sv'), np.atleast_2d(garr[:,i*3+1]))

                    dsf[k+'ssi'] = (('time','sv'), np.atleast_2d(garr[:,i*3+2]))

                if verbose:
                    print(time,'\r',end='')

                if data is None:
                    data = xarray.Dataset(dsf,coords={'time':[time],'sv':gsv})#, attrs={'toffset':toffset})
                else:
                    if len(fields)==1:
                        data = xarray.concat((data,
                                              xarray.Dataset(dsf,coords={'time':[time],'sv':gsv})),
                                              dim='time')
                    else: # general case, slower for different satellite systems all together
                        data = xarray.merge((data,
                                         xarray.Dataset(dsf,coords={'time':[time],'sv':gsv})))

    data.attrs['filename'] = f.name
    data.attrs['version'] = version
    #data.attrs['toffset'] = toffset

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
    if use is not None:
        fields = {k: fields[k] for k in use}

    return fields, header, Fmax
