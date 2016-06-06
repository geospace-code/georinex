#!/usr/bin/env python
"""
RINEX 2 OBS reader
under testing
Michael Hirsch, Greg Starr
MIT License

Program overviw:
1) read the OBS file header:   readHead()
2) parse the OBS file header, obtaining the times, satellites, and data measurement types:   makeSvset()
3) read the OBS files in blocks, where each block is one time interval of data (all sats, all measurements):  makeBlock()

makeBlock dumps the results into a preallocated pandas 3-D Panel with axes:
items / page: time
rows / major_axis: SV
column / minor_axis: data type P1,P2, etc.
"""
from __future__ import division #yes this is needed for py2 here.
from . import Path
import numpy as np
from itertools import chain
from datetime import datetime, timedelta
from pandas import DataFrame,Panel
from pandas.io.pytables import read_hdf
from io import BytesIO

def rinexobs(obsfn,odir=None,maxtimes=None):
    obsfn = Path(obsfn).expanduser()
    if odir: odir = Path(odir).expanduser()
        
    if obsfn.suffix.lower().endswith('o'): #raw text file
        with obsfn.open('r') as rinex:
            header,verRinex = readHead(rinex)
            print('{} is a RINEX {} file.'.format(obsfn,verRinex))
            (svnames,ntypes,obstimes,maxsv,obstypes) = makeSvSet(header,maxtimes,verRinex)
            blocks = makeBlocks(rinex,ntypes,maxsv,svnames,obstypes,obstimes)
    #%% save to disk (optional)
        if odir:
            h5fn = odir/obsfn.name.with_suffix('.h5')
            print('saving OBS data to {}'.format(h5fn))
            blocks.to_hdf(h5fn,key='OBS',mode='a',complevel=6,append=False)
    elif obsfn.suffix.lower().endswith('.h5'):
        blocks = read_hdf(obsfn,key='OBS')
        print('loaded OBS data from {} to {}'.format(blocks.items[0],blocks.items[-1]))
    return blocks

def TEC(data,startTime):
    # TODO: update to use datetime()
    for d in data:
        difference = []
        for i in range(6):
            difference.append(d[0][i]-startTime[i])
        time = difference[5]+60*difference[4]+3600*difference[3]+86400*difference[2]
        tec = (9.517)*(10**16)*(d[7]-d[2])
        TECs.append([time,tec])

def readHead(rinex):
    header = []
    while True:
        header.append(rinex.readline())
        if 'END OF HEADER' in header[-1]:
            break

    verRinex = float(grabfromhead(header,None,11,'RINEX VERSION / TYPE')[0][0])

    return header,verRinex

def grabfromhead(header,start,end,label):
    """
    returns (list of) strings from header based on label
    header: raw text of header (one big string)
    start: if unused set to None
    end: if unused set to None
    label: header text to match
    """
    return [l[start:end].split() for l in header if label in l[60:]]

def makeSvSet(header,maxtimes,verRinex):
    svnames=[]

#%% get number of obs types
    if '{:.2f}'.format(verRinex)=='3.01':
        #numberOfTypes = np.asarray(grabfromhead(header,1,6,"SYS / # / OBS TYPES")).astype(int).sum()  #total number of types for all satellites
        obstypes = grabfromhead(header,6,58,"SYS / # / OBS TYPES")
        #get unique obstypes FIXME should we make variables for each satellite family?
        obstypes = list(set(chain.from_iterable(obstypes)))
        numberOfTypes = len(obstypes) #unique
    elif '{:.1f}'.format(verRinex)=='2.1':
        numberOfTypes = int(grabfromhead(header,None,6,"# / TYPES OF OBSERV")[0][0])
        obstypes = grabfromhead(header,6,60,"# / TYPES OF OBSERV") # not [0] at end, because for obtypes>9, there are more than one list element!
        obstypes = list(chain.from_iterable(obstypes)) #need this for obstypes>9
        assert numberOfTypes == len(obstypes)
    else:
        raise NotImplementedError("RINEX version {} is not yet handled".format(verRinex))
#%% get number of satellites
    numberOfSv = int(grabfromhead(header,None,6,"# OF SATELLITES")[0][0])
#%% get observation time extents
    """
    here we take advantage of that there will always be whitespaces--for the data itself
    there aren't always whitespaces between data, so we have to get more explicit.
    Pynex currently takes the explicit indexing by text column instead of split().
    """
    firstObs = _obstime([l[:60] for l in header if "TIME OF FIRST OBS" in l[60:]][0].split(None))
    lastObs  = _obstime([l[:60] for l in header if "TIME OF LAST OBS" in l[60:]][0].split(None))
    interval_sec = float([l[:10] for l in header if "INTERVAL" in l[60:]][0])
    interval_delta = timedelta(seconds=int(interval_sec),
                               microseconds=int(interval_sec % 1)*100000)

    ntimes = int(np.ceil((lastObs-firstObs).total_seconds()/interval_delta.total_seconds()) + 1)
    if maxtimes is not None:
        ntimes = min(maxtimes,ntimes)
    obstimes = firstObs + interval_delta * np.arange(ntimes)
    #%% get satellite numbers
    linespersat = int(np.ceil(numberOfTypes / 9.))
    assert linespersat > 0

    satlines = [l[:60] for l in header if "PRN / # OF OBS" in l[60:]]

    if '{:0.1f}'.format(verRinex)=='2.1':
        #insert 0 if it doesn't exist for <10 satnum, RINEX files are inconsistent between header and block,
        #so let's force a sensible convention
        for i in range(numberOfSv):
            svnames.append(satlines[linespersat*i][3] +'{:02d}'.format(int(satlines[linespersat*i][4:6])))
    elif '{:0.2f}'.format(verRinex)=='3.01':
        raise NotImplementedError('far as we got so far')
    else:
        raise NotImplementedError("RINEX version {} is not yet handled".format(verRinex))


    return svnames,numberOfTypes, obstimes, numberOfSv,obstypes

def _obstime(fol):
    year = int(fol[0])
    if 80<= year <=99:
        year+=1900
    elif year<80: #because we might pass in four-digit year
        year+=2000
    return datetime(year=year, month=int(fol[1]), day= int(fol[2]),
                    hour= int(fol[3]), minute=int(fol[4]),
                    second=int(float(fol[5])),
                    microsecond=int(float(fol[5]) % 1) *100000
                    )

def _block2df(block,svnum,obstypes,svnames):
    """
    input: block of text corresponding to one time increment INTERVAL of RINEX file
    output: 2-D array of float64 data from block. Future: consider whether best to use Numpy, Pandas, or Xray.
    """
    nobs = len(obstypes)
    stride=3

    strio = BytesIO(block.encode())
    barr = np.genfromtxt(strio, delimiter=(14,1,1)*5).reshape((svnum,-1), order='C')

    data = barr[:,0:nobs*stride:stride]
   # lli  = barr[:,1:nobs*stride:stride]
   # ssi  = barr[:,2:nobs*stride:stride]

    #because of file format, array needs to be reshaped immediately upon read,
  # thus read_fwf may not be
    #suitable because it immediately returns a DataFrame.
#    barr = read_fwf(strio,
#                    colspecs=[(0,13), (13,14),(14,15),],
##                              (15,28),(28,29),(29,30),
##                              (30,43),(43,44),(45,45),
##                              (45,58),(58,59),(59,60)],
#                    skiprows=0,
#                    header=None,)
                    #names=obstypes)

    #FIXME: I didn't return the "signal strength" and "lock indicator" columns
    return DataFrame(index=svnames,columns=obstypes, data = data)



def makeBlocks(rinex,ntypes,maxsv,svnames,obstypes,obstimes):
    """
    inputs:
    rinex: file stream
    ntypes: number of observation types
    obstimes: datetime() of each observation
    obstypes: type of measurment e.g. P1, P2,...
    maxsv: maximum number of SVs the reciever saw in this file (i.e. across the entire obs. time)

    outputs:
    blocks: dimensions timeINTERVALs x maxsv x ntypes (page x row x col)
    """
    blocks = Panel(items=obstimes,
                   major_axis=svnames,
                   minor_axis=obstypes)

    for i in range(obstimes.size): #this means maxtimes was specified, otherwise we'd reach end of file
        sathead = rinex.readline()
        if not sathead: break  #EOF
        svnum = int(sathead[29:32])

        obslinespersat = int(np.ceil(ntypes/5))
        blockrows = svnum*obslinespersat

        satnames = sathead[32:68]
        for _ in range(int(np.ceil(svnum/12))-1):
            line = rinex.readline()
            sathead+=line
            satnames+=line[32:68] #FIXME is this right end?
        blocksvnames = satnumfixer(grouper(satnames,3,svnum))
#%% read this INTERVAL's text block
        block = ''.join(rinex.readline() for _ in range(blockrows))
        btime = _obstime(sathead[:26].split())
        bdf = _block2df(block,svnum,obstypes,blocksvnames)
        blocks.loc[btime,blocksvnames] = bdf

    return blocks

def satnumfixer(satnames):
    return [s[0] + '{:02d}'.format(int(s[1:3])) for s in satnames]

def grouper(txt,n,maxn):
    return [txt[n*i:n+n*i] for i in range(min(len(txt)//n,maxn))]
