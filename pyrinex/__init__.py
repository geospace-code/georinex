try:
    from pathlib import Path
    Path().expanduser()
except (ImportError,AttributeError):
    from pathlib2 import Path
#
import numpy as np
from datetime import datetime
from pandas import DataFrame,Panel4D,read_hdf
from io import BytesIO
from time import time

def readRinexNav(fn,odir=None):
    """
    Reads RINEX 2.11 NAV files
    Michael Hirsch
    It may actually be faster to read the entire file via f.read() and then .split()
    and asarray().reshape() to the final result, but I did it frame by frame.
    http://gage14.upc.es/gLAB/HTML/GPS_Navigation_Rinex_v2.11.html
    """
    fn = Path(fn).expanduser()
    if odir:
        odir = Path(odir).expanduser()

    startcol = 3 #column where numerical data starts
    nfloat=19 #number of text elements per float data number
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

    nav= DataFrame(data=np.concatenate((np.atleast_2d(sv).T,darr), axis=1),
                   index=epoch,
           columns=['sv','SVclockBias','SVclockDrift','SVclockDriftRate','IODE',
                'Crs','DeltaN','M0','Cuc','Eccentricity','Cus','sqrtA','TimeEph',
                'Cic','OMEGA','CIS','Io','Crc','omega','OMEGA DOT','IDOT',
                'CodesL2','GPSWeek','L2Pflag','SVacc','SVhealth','TGD','IODC',
                'TransTime','FitIntvl'])

    if odir:
        h5fn = odir/fn.name.with_suffix('.h5')
        print('saving NAV data to',str(h5fn))
        nav.to_hdf(h5fn,key='NAV',mode='a',complevel=6,append=False)

    return nav
# %% ====================================================================

def rinexobs(fn, h5file=None, returnHead=False, writeh5=False):
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
        lines.append('')
        header,version,headlines,headlength,obstimes,sats,svset = scan(lines)
        print('{} is a RINEX {} file, {} kB.'.format(fn,version, fn.stat().st_size//1000))
        if h5file==None:
            data = processBlocks(lines,header,obstimes,svset,headlines, headlength,sats)
        else:
            data = read_hdf(h5file, key='data')
        print("finished in {0:.2f} seconds".format(time()-tic))

    #write an h5 file if specified
    if writeh5:
        h5fn = fn.with_suffix('.h5')
        print('saving OBS data to',str(h5fn))
        data.to_hdf(h5fn, key='data',mode='w', format='table')

    #return info including header if desired
    if returnHead:
        return header,data
    else:
        return data


# this will scan the document for the header info and for the line on
# which each block starts
def scan(lines):
    header={}
    eoh=0
    for i,line in enumerate(lines):
        if "END OF HEADER" in line:
            eoh=i
            break
        if line[60:].strip() not in header:
            header[line[60:].strip()] = line[:60].strip()
        else:
            header[line[60:].strip()] += " "+line[:60].strip()
    verRinex = float(header['RINEX VERSION / TYPE'].split()[0])
    header['APPROX POSITION XYZ'] = [float(i) for i in header['APPROX POSITION XYZ'].split()]
    header['# / TYPES OF OBSERV'] = header['# / TYPES OF OBSERV'].split()
    header['# / TYPES OF OBSERV'][0] = int(header['# / TYPES OF OBSERV'][0])
    header['INTERVAL'] = float(header['INTERVAL'])

    headlines=[]
    headlength = []
    obstimes=[]
    sats=[]
    svset=set()
    i=eoh+1
    while True:
        if not lines[i]: break
        if not int(lines[i][28]):
            #no flag or flag=0
            headlines.append(i)
            obstimes.append(_obstime([lines[i][1:3],lines[i][4:6],
                                   lines[i][7:9],lines[i][10:12],
                                   lines[i][13:15],lines[i][16:26]]))
            numsvs = int(lines[i][30:32])  # Number of visible satellites
            headlength.append(1 + numsvs//12)
            if(numsvs>12):
                sp=[]
                for s in range(numsvs):
                    sp.append(int(lines[i][33+(s%12)*3:35+(s%12)*3]))
                    if s>0 and s%12 == 0:
                        i+= 1  # For every 12th satellite there will be a new row with satellite names
                sats.append(sp)
            else:
                sats.append([int(lines[i][33+s*3:35+s*3]) for s in range(numsvs)])

            i+=numsvs*int(np.ceil(header['# / TYPES OF OBSERV'][0]/5))+1
        else:
            #there was a comment or some header info
            flag=int(lines[i][28])
            if(flag!=4):
                print(flag)
            skip=int(lines[i][30:32])
            i+=skip+1
    for sv in sats:
        svset = svset.union(set(sv))

    return header,verRinex,headlines,headlength,obstimes,sats,svset



def processBlocks(lines,header,obstimes,svset,headlines, headlength,sats):

    obstypes = header['# / TYPES OF OBSERV'][1:]
    blocks = np.nan*np.ones((len(obstypes),max(svset)+1,len(obstimes),3))

    for i in range(len(headlines)):
        linesinblock = len(sats[i])*int(np.ceil(header['# / TYPES OF OBSERV'][0]/5))
        block = ''.join(lines[headlines[i]+headlength[i]:headlines[i]+linesinblock+headlength[i]])
        bdf = _block2df(block,obstypes,sats[i],len(sats[i]))
        blocks[:,np.asarray(sats[i],int),i,:] = bdf

    blocks = Panel4D(blocks,
                     labels=obstypes,
                     items=np.arange(max(svset)+1),
                     major_axis=obstimes,
                     minor_axis=['data','lli','ssi'])
    blocks = blocks[:,list(svset),:,:]

    return blocks


def _obstime(fol):
    year = int(fol[0])
    if 80<= year <=99:
        year+=1900
    elif year<80: #because we might pass in four-digit year
        year+=2000
    return datetime(year=year, month=int(fol[1]), day= int(fol[2]),
                    hour= int(fol[3]), minute=int(fol[4]),
                    second=int(float(fol[5])),
                    microsecond=int(float(fol[5]) % 1 * 100000)
                    )

def _block2df(block,obstypes,svnames,svnum):
    """
    input: block of text corresponding to one time increment INTERVAL of RINEX file
    output: 2-D array of float64 data from block. Future: consider whether best to use Numpy, Pandas, or Xray.
    """
    nobs = len(obstypes)
    stride=3

    strio = BytesIO(block.encode())
    barr = np.genfromtxt(strio, delimiter=(14,1,1)*5).reshape((svnum,-1), order='C')

    data = barr[:,0:nobs*stride:stride]
    lli  = barr[:,1:nobs*stride:stride]
    ssi  = barr[:,2:nobs*stride:stride]

    data = np.vstack(([data],[lli],[ssi])).T

    return data

