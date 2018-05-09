from pathlib import Path
import numpy as np
from math import ceil
from datetime import datetime
from io import BytesIO
import xarray
from typing import Union
#
STARTCOL2 = 3 #column where numerical data starts for RINEX 2

F = ('SVclockBias','SVclockDrift','SVclockDriftRate','IODE','Crs','DeltaN',
     'M0','Cuc','Eccentricity','Cus','sqrtA','Toe','Cic','omega0','Cis','Io',
     'Crc','omega','OmegaDot','IDOT','CodesL2','GPSWeek','L2Pflag','SVacc',
     'SVhealth','TGD','IODC','TransTime','FitIntvl')

def _rinexnav2(fn:Path) -> xarray.Dataset:
    """
    Reads RINEX 2.11 NAV files
    Michael Hirsch, Ph.D.
    SciVision, Inc.

    http://gage14.upc.es/gLAB/HTML/GPS_Navigation_Rinex_v2.11.html
    ftp://igs.org/pub/data/format/rinex211.txt
    """
    fn = Path(fn).expanduser()

    Nl = 7 #number of additional lines per record, for RINEX 2 NAV
    Nf = 29 # number of fields per record, for RINEX 2 NAV
    assert len(F) == 29
    Lf = 19 # string length per field

    sv = []; epoch=[]; raws=[]

    with fn.open('r') as f:
        """verify RINEX version, and that it's NAV"""
        line = f.readline()
        ver = float(line[:9])
        assert int(ver)==2,'see _rinexnav3() for RINEX 3.0 files'
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
        for l in f:
            # format I2 http://gage.upc.edu/sites/default/files/gLAB/HTML/GPS_Navigation_Rinex_v2.11.html
            sv.append(int(l[:2]))
            # format I2
            year = int(l[3:5])  # yes, skipping one unused columsn
            if 80 <= year <=99:
                year += 1900
            elif year<80: #good till year 2180
                year += 2000

            epoch.append(datetime(year =year,
                                  month   =int(l[6:8]),
                                  day     =int(l[9:11]),
                                  hour    =int(l[12:14]),
                                  minute  =int(l[15:17]),
                                  second  =int(l[17:20]),  # python reads second and fraction in parts
                                  microsecond=int(float(l[17:22]) % 1 * 1000000)))
            """
            now get the data as one big long string per SV
            """
            raw = l[22:79]  # NOTE: MUST be 79, not 80 due to some files that put \n a character early!
            for _ in range(Nl):
                raw += f.readline()[STARTCOL2:79]
            # one line per SV
            raws.append(raw.replace('D','E'))
# %% parse
    # for RINEX 2, don't use delimiter
    darr = np.empty((len(raws), Nf))

    for i,r in enumerate(raws):
        darr[i,:] = np.genfromtxt(BytesIO(r.encode('ascii')), delimiter=[Lf]*Nf)  # must have *Nf to avoid false nan on trailing spaces

    dsf = {f: ('time',d) for (f,d) in zip(F,darr.T)}
    dsf.update({'sv':('time',sv)})

    nav = xarray.Dataset(dsf,
                          coords={'time':epoch},
                          attrs={'RINEX version':ver,
                                 'RINEX filename':fn.name}
                          )

    return nav


def _scan2(fn:Path, use:Union[str,list,tuple], verbose:bool=False) -> xarray.Dataset:
  """
   procss RINEX OBS data
  """

  if (not use or not use[0].strip() or
      isinstance(use,str) and use.lower() in ('m','all') or
      isinstance(use,(tuple,list,np.ndarray)) and use[0].lower() in ('m','all')):

      use = None


  with fn.open('r') as f:
    header={}
    Nobs = None
    # Capture header info
    for l in f:
        if "END OF HEADER" in l:
            break

        h = l[60:80]
        c = l[:60]
        if '# / TYPES OF OBSERV' in h:
            if Nobs is None:
                Nobs = int(c[:6])
                c = c[6:]

        if h.strip() not in header: #Header label
            header[h.strip()] = c
            # string with info
        else:
            header[h.strip()] += " " + c
            #concatenate to the existing string
# %% sanity check that MANDATORY RINEX 2 headers exist
    for h in ('RINEX VERSION / TYPE', 'APPROX POSITION XYZ', 'INTERVAL'):
        if not h in header:
            raise IOError('Mandatory RINEX 2 headers are missing from {fn}, is it a valid RINEX 2 file?')
# %% file seems OK, keep processing
    verRinex = float(header['RINEX VERSION / TYPE'][:9])  # %9.2f
    # list with x,y,z cartesian
    header['APPROX POSITION XYZ'] = [float(j) for j in header['APPROX POSITION XYZ'].split()]
    #observation types
    fields = header['# / TYPES OF OBSERV'].split()
    assert Nobs == len(fields), 'header read incorrectly'

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
        if verbose:
            print(time,'\r',end="")

        try:
            toffset = l[68:80]
        except ValueError:
            toffset = None
# %% get SV indices
        Nsv = int(l[29:32])  # Number of visible satellites this time %i3
        # get first 12 SV ID's
        sv = _getSVlist(l, min(12,Nsv), [])

        # any more SVs?
        n = Nsv-12
        while n > 0:
            l = f.readline()
            sv = _getSVlist(l, min(12,n), sv)
            n -= 12
        assert Nsv == len(sv), 'satellite list read incorrectly'
# %% select one, a few, or all satellites
        if use is not None:
            iuse = [i for i,s in enumerate(sv) if s[0] in use]
        else:
            iuse = slice(None)

        gsv = np.array(sv)[iuse]
        Ngsv = len(gsv)
# %% assign data for each time step
        darr = np.empty((Nsv,Nobs*3))
        Nl_sv = int(ceil(Nobs/5))  # CEIL needed for Py27 only.

        for i,s in enumerate(sv):
            raw = ''
            for _ in range(Nl_sv):
                raw += f.readline()[:80]

            if use is not None and not s[0] in use: # save a lot of time by not processing discarded satellites
                continue

            raw = raw.replace('\n',' ')  # some files truncate and put \n in data space.

            darr[i,:] = np.genfromtxt(BytesIO(raw.encode('ascii')), delimiter=[Ngsv,1,1]*Nobs)
# % select only "used" satellites
        garr = darr[iuse,:]
        dsf = {}
        for i,k in enumerate(fields):
            dsf[k] = (('time','sv'),np.atleast_2d(garr[:,i*3]))
            if not k in ('S1','S2'): # FIXME which other should be excluded?
                if k in ('L1','L2'):
                    dsf[k+'lli'] = (('time','sv'),np.atleast_2d(garr[:,i*3+1]))
                dsf[k+'ssi'] = (('time','sv'),np.atleast_2d(garr[:,i*3+2]))

        if data is None:
            data = xarray.Dataset(dsf,coords={'time':[time],'sv':gsv}, attrs={'toffset':toffset})
        else:
            data = xarray.concat((data,
                                  xarray.Dataset(dsf,coords={'time':[time],'sv':gsv}, attrs={'toffset':toffset})),
                                  dim='time')

    data.attrs['filename'] = f.name
    data.attrs['RINEX version'] = verRinex

    return data


def _getSVlist(l:str, N:int, sv:list) -> list:
    """ parse a line of text from RINEX2 SV list"""
    for i in range(N):
        s = l[32+i*3:35+i*3].strip()
        if not s.strip():
            raise ValueError('did not get satellite names from {}'.format(l))
        sv.append(s)

    return sv


def _obstime(fol:str) -> datetime:
    """
    Python >= 3.7 supports nanoseconds.  https://www.python.org/dev/peps/pep-0564/
    Python < 3.7 supports microseconds.
    """
    year = int(fol[0])
    if 80 <= year <=99:
        year+=1900
    elif year<80: #because we might pass in four-digit year
        year+=2000

    return datetime(year=year, month=int(fol[1]), day= int(fol[2]),
                    hour= int(fol[3]), minute=int(fol[4]),
                    second=int(float(fol[5])),
                    microsecond=int(float(fol[5]) % 1 * 1000000)
                    )
