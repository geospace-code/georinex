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

