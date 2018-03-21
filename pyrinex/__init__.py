from __future__ import division  # absolutely needed for Py27 or strange behavior
try:
    from pathlib import Path
    Path().expanduser()
except (ImportError,AttributeError):
    from pathlib2 import Path
#
import logging
import numpy as np
from datetime import datetime
import xarray
from io import BytesIO
from time import time

"""https://github.com/mvglasow/satstat/wiki/NMEA-IDs"""
SBAS=100 # offset for ID
GLONASS=37
QZSS=192
BEIDOU=0

STARTCOL2 = 3 #column where numerical data starts for RINEX 2
STARTCOL3 = 4 #column where numerical data starts for RINEX 3
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

def _newnav(l):
    sv = l[:3]

    svtype = sv[0]

    if svtype == 'G':
        sv = int(sv[1:]) + 0
        fields = ['sv','aGf0','aGf1','SVclockDriftRate',
                  'IODE','Crs','DeltaN','M0',
                  'Cuc','Eccentricity','Cus','sqrtA',
                  'Toe','Cic','OMEGA0','Cis',
                  'Io','Crc','omega','OMEGA DOT',
                  'IDOT','CodesL2','GPSWeek','L2Pflag',
                  'SVacc','SVhealth','TGD','IODC',
                  'TransTime','FitIntvl']
    elif svtype == 'C':
        sv = int(sv[1:]) + BEIDOU
    elif svtype == 'R':
        sv = int(sv[1:]) + GLONASS
    elif svtype == 'S':
        sv = int(sv[1:]) + SBAS
        fields=['sv','aGf0','aGf1','MsgTxTime',
                'X','dX','dX2','SVhealth',
                'Y','dY','dY2','URA',
                'Z','dZ','dZ2','IODN']
    elif svtype == 'J':
        sv = int(sv[1:]) + QZSS
    elif svtype == 'E':
        raise NotImplementedError('Galileo PRN not yet known')
    else:
        raise ValueError('Unknown SV type {}'.format(sv[0]))


    year = int(l[4:8]) # I4

    t = datetime(year = year,
                  month   =int(l[9:11]),
                  day     =int(l[12:14]),
                  hour    =int(l[15:17]),
                  minute  =int(l[18:20]),
                  second  =int(l[21:23]))

    return sv, t, fields,svtype


def _rinexnav3(fn, ofn=None):
    """
    Reads RINEX 3.0 NAV files

    http://www.gage.es/sites/default/files/gLAB/HTML/SBAS_Navigation_Rinex_v3.01.html
    """
    fn = Path(fn).expanduser()

    svs = []; epoch=[]; raws=''

    with fn.open('r') as f:
        """verify RINEX version, and that it's NAV"""
        line = f.readline()
        assert int(float(line[:9]))==3,'see rinexnav2() for RINEX 3.0 files'
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
            sv,t,fields,svtype = _newnav(line)
            svs.append(sv)
            epoch.append(t)
# %% get the data as one big long string per SV, unknown # of lines per SV
            raw = line[23:80]

            while True:
                line = f.readline()
                if not line or line[0] != ' ': # new SV
                    break

                raw += line[STARTCOL3:80]
            # one line per SV
            raws += raw + '\n'

            if not line: # EOF
                break

    raws = raws.replace('D','E')
# %% parse
    darr = np.genfromtxt(BytesIO(raws.encode('ascii')),
                         delimiter=19)

    nav= xarray.DataArray(data=np.concatenate((np.atleast_2d(svs).T, darr), axis=1),
                coords={'t':epoch,
                'data':fields},
                dims=['t','data'],
                name=svtype)

    if ofn:
        ofn = Path(ofn).expanduser()
        print('saving NAV data to',ofn)
        if ofn.is_file():
            wmode='a'
        else:
            wmode='w'
        nav.to_netcdf(str(ofn), group='NAV', mode=wmode)

    return nav


def _rinexnav2(fn, ofn=None):
    """
    Reads RINEX 2.11 NAV files
    Michael Hirsch, Ph.D.
    SciVision, Inc.

    It may actually be faster to read the entire file via f.read() and then .split()
    and asarray().reshape() to the final result, but I did it frame by frame since RINEX files
    may be enormous.

    http://gage14.upc.es/gLAB/HTML/GPS_Navigation_Rinex_v2.11.html
    ftp://igs.org/pub/data/format/rinex211.txt
    """
    fn = Path(fn).expanduser()

    Nl = 7 #number of additional lines per record, for RINEX 2 NAV
    Nf = 29 # number of fields per record, for RINEX 2 NAV
    Lf = 19 # string length per field

    sv = []; epoch=[]; raws=[]

    with fn.open('r') as f:
        """verify RINEX version, and that it's NAV"""
        line = f.readline()
        assert int(float(line[:9]))==2,'see rinexnav3() for RINEX 3.0 files'
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
                                  microsecond=int(l[21])*100000))
            """
            now get the data as one big long string per SV
            """
            raw = l[22:79]  # :79, NOT :80
            for _ in range(Nl):
                raw += f.readline()[STARTCOL2:79]
            # one line per SV
            raws.append(raw.replace('D','E'))
# %% parse
    # for RINEX 2, don't use delimiter
    Nt = len(raws)
    darr = np.empty((Nt, Nf))

    for i,r in enumerate(raws):
        darr[i,:] = np.genfromtxt(BytesIO(r.encode('ascii')), delimiter=[Lf]*Nf)

    nav = xarray.Dataset({'sv':              ('time',sv),
                          'SVclockBias':     ('time',darr[:,0]),
                          'SVclockDrift':    ('time',darr[:,1]),
                          'SVclockDriftRate':('time',darr[:,2]),
                          'IODE':            ('time',darr[:,3]),
                          'Crs':             ('time',darr[:,4]),
                          'DeltaN':          ('time',darr[:,5]),
                          'M0':              ('time',darr[:,6]),
                          'Cuc':             ('time',darr[:,7]),
                          'Eccentricity':    ('time',darr[:,8]),
                          'Cus':             ('time',darr[:,9]),
                          'sqrtA':           ('time',darr[:,10]),
                          'Toe':             ('time',darr[:,11]),
                          'Cic':             ('time',darr[:,12]),
                          'OMEGA0':          ('time',darr[:,13]),
                          'Cis':             ('time',darr[:,14]),
                          'Io':              ('time',darr[:,15]),
                          'Crc':             ('time',darr[:,16]),
                          'omega':           ('time',darr[:,17]),
                          'OMEGA DOT':       ('time',darr[:,18]),
                          'IDOT':            ('time',darr[:,19]),
                          'CodesL2':         ('time',darr[:,20]),
                          'GPSWeek':         ('time',darr[:,21]),
                          'L2Pflag':         ('time',darr[:,22]),
                          'SVacc':           ('time',darr[:,23]),
                          'SVhealth':        ('time',darr[:,24]),
                          'TGD':             ('time',darr[:,25]),
                          'IODC':            ('time',darr[:,26]),
                          'TransTime':       ('time',darr[:,27]),
                          'FitIntvl':        ('time',darr[:,28]),
                          },
                          coords={'time':epoch}
                          )


    if ofn:
        ofn = Path(ofn).expanduser()
        print('saving NAV data to',ofn)
        if ofn.is_file():
            wmode='a'
        else:
            wmode='w'
        nav.to_netcdf(ofn, group='NAV', mode=wmode)

    return nav
# %% Observation File
def rinexobs(fn, ofn=None):
    """
    Program overviw:
    1) scan the whole file for the header and other information using scan(lines)
    2) each epoch is read and the information is put in a 4-D xarray.DataArray
    3)  rinexobs can also be sped up with if an h5 file is provided,
        also rinexobs can save the rinex file as an h5. The header will
        be returned only if specified.

    rinexobs() returns the data in a 4-D xarray.DataArray, [Parameter,Sat #,time,data/loss of lock/signal strength]
    """
    #open file, get header info, possibly speed up reading data with a premade h5 file
    fn = Path(fn).expanduser()
    with fn.open('r') as f:
        tic = time()
        lines = f.read().splitlines(True)
        header,version,headlines,headlength,obstimes,sats,svset = scan(lines)
        print(fn,'RINEX',version,'file',fn.stat().st_size//1000,'kB.')
        if fn.suffix=='.nc':
            data = xarray.open_dataarray(str(fn), group='OBS')
        elif fn.suffix=='.h5':
            logging.warning('HDF5 is deprecated in this program, please use NetCDF format')
            import pandas
            data = pandas.read_hdf(fn, key='OBS')
        else:
            data = processBlocks(lines,header,obstimes,svset,headlines, headlength,sats)

        print("finished in {:.2f} seconds".format(time()-tic))

    #write an h5 file if specified
    if ofn:
        ofn = Path(ofn).expanduser()
        print('saving OBS data to',ofn)
        if ofn.is_file():
            wmode='a'
        else:
            wmode='w'
        data.to_netcdf(str(ofn), group='OBS', mode=wmode)

    return data,header



# this will scan the document for the header info and for the line on
# which each block starts
def scan(L):
    header={}
    # Capture header info
    for i,l in enumerate(L):
        if "END OF HEADER" in l:
            i+=1 # skip to data
            break
        if l[60:80].strip() not in header: #Header label
            header[l[60:80].strip()] = l[:60]  # don't strip for fixed-width parsers
            # string with info
        else:
            header[l[60:80].strip()] += " "+l[:60]
            #concatenate to the existing string

    verRinex = float(header['RINEX VERSION / TYPE'][:9])  # %9.2f
    # list with x,y,z cartesian
    header['APPROX POSITION XYZ'] = [float(j) for j in header['APPROX POSITION XYZ'].split()]
    #observation types
    header['# / TYPES OF OBSERV'] = header['# / TYPES OF OBSERV'].split()
    #turn into int number of observations
    header['# / TYPES OF OBSERV'][0] = int(header['# / TYPES OF OBSERV'][0])
    header['INTERVAL'] = float(header['INTERVAL'][:10])

    headlines=[]
    headlength = []
    obstimes=[]
    sats=[]
    svset=set()
# %%
    while i < len(L):
        if int(L[i][28]) in (0,1,5,6): # EPOCH FLAG
            headlines.append(i)
            obstimes.append(_obstime([L[i][1:3],  L[i][4:6],
                                      L[i][7:9],  L[i][10:12],
                                      L[i][13:15],L[i][16:26]]))
            numsvs = int(L[i][29:32])  # Number of visible satellites %i3
            headlength.append(1 + numsvs//12)  # number of lines in header
            if numsvs > 12:
                sv=[]
                for s in range(numsvs):
                    # TODO this discards G R
                    if s>0 and s%12 == 0:
                        i += 1  # every 12th satellite will add new row with satellite names
                    sv.append(int(L[i][33+(s%12)*3:35+(s%12)*3]))
                sats.append(sv)
            else:
                sats.append([int(L[i][33+s*3:35+s*3]) for s in range(numsvs)])

            skip = numsvs*int(np.ceil(header['# / TYPES OF OBSERV'][0]/5))
            i += skip + 1
        else: #there was a comment or some header info
            flag=int(L[i][28])

            if(flag!=4):
                print(flag)
            skip=int(L[i][30:32])
            i+=skip+1
# %% get every SV that appears at any time in the file, for master index
    for sv in sats:
        svset = svset.union(set(sv))

    return header,verRinex,headlines,headlength,obstimes,sats,svset


def processBlocks(lines,header,obstimes,svset,ihead, headlength,sats):
    #lines,header,obstimes,svset,ihead, headlength,sats
    obstypes = header['# / TYPES OF OBSERV'][1:]
    blocks = np.nan*np.ones((len(obstypes),
                             max(svset)+1,
                             len(obstimes),
                             3))

    for i in range(len(ihead)):
        linesinblock = len(sats[i])*int(np.ceil(header['# / TYPES OF OBSERV'][0]/5.)) #nsats x observations
        # / 5 there is space for 5 observables per line

        block = ''.join(lines[ihead[i]+headlength[i]:ihead[i]+linesinblock+headlength[i]])
        bdf = _block2df(block,obstypes,sats[i],len(sats[i]))
        blocks[:, sats[i], i, :] = bdf

    blocks = xarray.DataArray(data=blocks,
                                          coords={'obs':obstypes,
                                                       'sv':np.arange(max(svset)+1),
                                                       't':obstimes,
                                                       'type':['data','lli','ssi']},
                                          dims=['obs','sv','t','type'])

    blocks = blocks[:,list(svset),:,:]  # remove unused SV numbers

    return blocks


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

def _block2df(block, obstypes, svnames, svnum):
    """
    input: block of text corresponding to one time increment INTERVAL of RINEX file
    output: 2-D array of float64 data from block.
    """
    assert isinstance(svnum,int)
    N = len(obstypes)
    S = 3  # stride

    sio = BytesIO(block.encode('ascii'))
    barr = np.genfromtxt(sio, delimiter=(svnum,1,1)*5).reshape((svnum,-1), order='C')

    #iLLI = [obstypes.index(l) for l in ('L1','L2')]

    data = barr[:,0:N*S:S].T
    lli  = barr[:,1:N*S:S].T #[:,iLLI]
    ssi  = barr[:,2:N*S:S].T

    data = np.stack((data,lli,ssi),2) # Nobs x Nsat x 3

    return data

