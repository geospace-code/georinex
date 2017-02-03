#!/usr/bin/env python
"""
RINEX 2 OBS reader
under testing
Michael Hirsch, Greg Starr
MIT License

Program overviw:
1) scan the whole file for the header and other information using scan(lines)
2) each epoch is read and the information is put in a 4D Panel
3)  rinexobs can also be sped up with if an h5 file is provided, 
    also rinexobs can save the rinex file as an h5. The header will
    be returned only if specified.    

rinexobs() returns the data in a 4D Panel, [Parameter,Sat #,time,data/loss of lock/signal strength]
"""
from __future__ import division #yes this is needed for py2 here.
import numpy as np
from pandas import Panel4D
from pandas.io.pytables import read_hdf
from io import BytesIO
from os.path import splitext,expanduser,getsize
import time
from datetime import datetime

def rinexobs(rinexfile,h5file=None,returnHead=False,writeh5=False):
    
    #open file, get header info, possibly speed up reading data with a premade h5 file
    stem,ext = splitext(expanduser(rinexfile))
    with open(rinexfile,'r') as f:
        t=time.time()
        lines = f.read().splitlines(True)
        lines.append('')
        header,version,headlines,headlength,obstimes,sats,svset = scan(lines)
        print('{} is a RINEX {} file, {} kB.'.format(rinexfile,version,getsize(rinexfile)/1000.0))
        if h5file==None:
            data = processBlocks(lines,header,obstimes,svset,headlines, headlength,sats)
        else:
            data = read_hdf(h5file,key='data')
        print("finished in {0:.2f} seconds".format(time.time()-t))
        
    #write an h5 file if specified
    if writeh5:
        h5fn = stem + '.h5'
        print('saving OBS data to {}'.format(h5fn))
        data.to_hdf(h5fn,key='data',mode='w',format='table')
        
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

