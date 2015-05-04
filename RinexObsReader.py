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
from __future__ import division
import numpy as np
try:
    import matplotlib.pyplot as plt
except ImportError as e:
    print('skipped loading matplotlib (for selftest)  {}'.format(e))
from itertools import chain
from datetime import datetime, timedelta
from pandas import DataFrame,Panel
from pandas.io.pytables import read_hdf
from os.path import splitext,expanduser
from io import BytesIO

def rinexobs(obsfn,writeh5,maxtimes=None):
    stem,ext = splitext(expanduser(obsfn))
    if ext[-1].lower() == 'o': #raw text file
        with open(obsfn,'r') as rinex:
            header = readHead(rinex)
            (svnames,types,obstimes,maxsv,obstypes) = makeSvSet(header,maxtimes)
            blocks = makeBlocks(rinex,types,maxsv,svnames,obstypes,obstimes)
    #%% save to disk (optional)
        if writeh5:
            h5fn = stem + '.h5'
            print('saving OBS data to {}'.format(h5fn))
            blocks.to_hdf(h5fn,key='OBS',mode='a',complevel=6,append=False)
    elif ext.lower() == '.h5':
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

    return header

def makeSvSet(header,maxtimes):
    svnames=[]
#%% get number of obs types
    numberOfTypes = int([l[:6] for l in header if "# / TYPES OF OBSERV" in l[60:]][0])
    obstypes = [l[6:60].split() for l in header if "# / TYPES OF OBSERV" in l[60:]] # not [0] at end, because for obtypes>9, there are more than one list element!
    obstypes = list(chain.from_iterable(obstypes)) #need this for obstypes>9
#%% get number of satellites
    numberOfSv = int([l[:6] for l in header if "# OF SATELLITES" in l[60:]][0])
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
    linespersat = int(np.ceil(numberOfTypes / 9))
    assert linespersat > 0

    satlines = [l[:60] for l in header if "PRN / # OF OBS" in l[60:]]

    #insert 0 if it doesn't exist for <10 satnum, RINEX files are inconsistent between header and block,
    #so let's force a sensible convention
    for i in range(numberOfSv):
        svnames.append(satlines[linespersat*i][3] +'{:02d}'.format(int(satlines[linespersat*i][4:6])))

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
    lli  = barr[:,1:nobs*stride:stride]
    ssi  = barr[:,2:nobs*stride:stride]

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


if __name__ == '__main__':
    from argparse import ArgumentParser
    p = ArgumentParser('our program to read RINEX 2 OBS files')
    p.add_argument('obsfn',help='RINEX 2 obs file',type=str)
    p.add_argument('--h5',help='write observation data for faster loading',action='store_true')
    p.add_argument('--maxtimes',help='Choose to read only the first N INTERVALs of OBS file',type=int,default=None)
    p.add_argument('--profile',help='profile code for debugging',action='store_true')
    p = p.parse_args()

    if p.profile:
        import cProfile
        from pstats import Stats
        profFN = 'RinexObsReader.pstats'
        cProfile.run('rinexobs(p.obsfn,p.h5,p.maxtimes)',profFN)
        Stats(profFN).sort_stats('time','cumulative').print_stats(20)
    else:
        blocks = rinexobs(p.obsfn,p.h5,p.maxtimes)
#%% plot
        plt.plot(blocks.items,blocks.ix[:,0,'P1'])
        plt.xlabel('time [UTC]')
        plt.ylabel('P1')
        plt.show()
#%% TEC can be made another column (on the minor_axis) of the blocks Panel.
