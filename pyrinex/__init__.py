try:
    from pathlib import Path
    Path().expanduser()
except (ImportError,AttributeError):
    from pathlib2 import Path
#
import numpy as np
from datetime import datetime
from pandas import read_hdf
import xarray
from io import BytesIO
from time import time

def rinexnav(fn, ofn=None):
    """
    Reads RINEX 2.11 NAV files
    Michael Hirsch
    It may actually be faster to read the entire file via f.read() and then .split()
    and asarray().reshape() to the final result, but I did it frame by frame.
    http://gage14.upc.es/gLAB/HTML/GPS_Navigation_Rinex_v2.11.html
    """
    fn = Path(fn).expanduser()

    startcol = 3 #column where numerical data starts
    N = 7 #number of lines per record

    sv = []; epoch=[]; raws=''

    with fn.open('r') as f:
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
            year = int(l[3:5])
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
            raw = l[22:80]
            for _ in range(N):
                raw += f.readline()[startcol:80]
            # one line per SV
            raws += raw + '\n'

    raws = raws.replace('D','E')
# %% parse
    darr = np.genfromtxt(BytesIO(raws.encode('ascii')))

    nav= xarray.DataArray(data=np.concatenate((np.atleast_2d(sv).T,darr), axis=1),
                                      coords={'t':epoch,
                                                  'data':['sv','SVclockBias','SVclockDrift','SVclockDriftRate','IODE',
                'Crs','DeltaN','M0','Cuc','Eccentricity','Cus','sqrtA','TimeEph',
                'Cic','OMEGA','CIS','Io','Crc','omega','OMEGA DOT','IDOT',
                'CodesL2','GPSWeek','L2Pflag','SVacc','SVhealth','TGD','IODC',
                'TransTime','FitIntvl']},
                                     dims=['t','data'])

    if ofn:
        ofn = Path(ofn).expanduser()
        print('saving NAV data to',str(ofn))
        if ofn.is_file():
            wmode='a'
        else:
            wmode='w'
        nav.to_hdf(ofn, key='NAV',mode=wmode, complevel=6)

    return nav
# %% ====================================================================

def rinexobs(fn, ofn=None):
    """
    Program overviw:
    1) scan the whole file for the header and other information using scan(lines)
    2) each epoch is read and the information is put in a 4D Panel
    3)  rinexobs can also be sped up with if an h5 file is provided,
        also rinexobs can save the rinex file as an h5. The header will
        be returned only if specified.

    rinexobs() returns the data in a 4D Panel, [Parameter,Sat #,time,data/loss of lock/signal strength]
    """
    #open file, get header info, possibly speed up reading data with a premade h5 file
    fn = Path(fn).expanduser()
    with fn.open('r') as f:
        tic = time()
        lines = f.read().splitlines(True)
        header,version,headlines,headlength,obstimes,sats,svset = scan(lines)
        print('{} is a RINEX {} file, {} kB.'.format(fn,version, fn.stat().st_size//1000))
        if fn.suffix=='.h5':
            data = read_hdf(fn, key='data')
        else:
            data = processBlocks(lines,header,obstimes,svset,headlines, headlength,sats)

        print("finished in {0:.2f} seconds".format(time()-tic))

    #write an h5 file if specified
    if ofn:
        ofn = Path(ofn).expanduser()
        print('saving OBS data to',str(ofn))
        if ofn.is_file():
            wmode='a'
        else:
            wmode='w'
            # https://github.com/pandas-dev/pandas/issues/5444
        data.to_hdf(ofn, key='OBS', mode=wmode, complevel=6,format='table')

    return data,header



# this will scan the document for the header info and for the line on
# which each block starts
def scan(L):
    header={}
    for i,l in enumerate(L):
        if "END OF HEADER" in l:
            i+=1 # skip to data
            break
        if l[60:80].strip() not in header:
            header[l[60:80].strip()] = l[:60]  # don't strip for fixed-width parsers
        else:
            header[l[60:80].strip()] += " "+l[:60]
    verRinex = float(header['RINEX VERSION / TYPE'][:9])  # %9.2f
    header['APPROX POSITION XYZ'] = [float(i) for i in header['APPROX POSITION XYZ'].split()]
    header['# / TYPES OF OBSERV'] = header['# / TYPES OF OBSERV'].split()
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
                        i += 1  # For every 12th satellite there will be a new row with satellite names
                    sv.append(int(L[i][33+(s%12)*3:35+(s%12)*3]))
                sats.append(sv)
            else:
                sats.append([int(L[i][33+s*3:35+s*3]) for s in range(numsvs)])

            i += numsvs*int(np.ceil(header['# / TYPES OF OBSERV'][0]/5))+1
        else:
            #there was a comment or some header info
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

    obstypes = header['# / TYPES OF OBSERV'][1:]
    blocks = np.nan*np.ones((len(obstypes),
                             max(svset)+1,
                             len(obstimes),
                             3))

    for i in range(len(ihead)):
        linesinblock = len(sats[i])*int(np.ceil(header['# / TYPES OF OBSERV'][0]/5))
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
    output: 2-D array of float64 data from block. Future: consider whether best to use Numpy, Pandas, or Xray.
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

