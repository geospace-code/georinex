"""
Reads RINEX 2.1 NAV files
by Michael Hirsch
bostonmicrowave.com
LGPLv3+
"""
from __future__ import division
from os.path import expanduser
import numpy as np
from datetime import datetime
from pandas import DataFrame,Panel
import sys
if sys.version_info<(3,):
    py3 = False
    from StringIO import StringIO
else:
    from io import BytesIO
    py3 = True

def readRINEXnav(fn):
    """
    Michael Hirsch
    It may actually be faster to read the entire file via f.read() and then .split()
    and asarray().reshape() to the final result, but I did it frame by frame.
    http://gage14.upc.es/gLAB/HTML/GPS_Navigation_Rinex_v2.11.html
    """
    startcol = 3 #column where numerical data starts
    nfloat=19 #number of text elements per float data number
    yb = 2000 # TODO I'm assuming it's the 21st century!
    nline=7 #number of lines per record
    nsat = 32 #TODO account for more than just "G"?

    with open(expanduser(fn),'r') as f:
        #find end of header, which has non-constant length
        while True:
            if 'END OF HEADER' in f.readline(): break
        #handle frame by frame
        sv = []; epoch=[]; raws=''
        while True:
            headln = f.readline()
            if not headln: break
            #handle the header
            sv.append(headln[:2])
            epoch.append(datetime(year =yb+int(headln[2:5]),
                                  month   =int(headln[5:8]),
                                  day     =int(headln[8:11]),
                                  hour    =int(headln[11:14]),
                                  minute  =int(headln[14:17]),
                                  second  =int(headln[17:20]),
                                  microsecond=int(headln[21])*100000))
            """
            now get the data.
            Use rstrip() to chomp newlines consistently on Windows and Python 2.7/3.4
            Specifically [:-1] doesn't work consistently as .rstrip() does here.
            """
            raw = (headln[22:].rstrip() +
                    ''.join(f.readline()[startcol:].rstrip() for _ in range(nline)))
            raws += raw + '\n'

    raws = raws.replace('D','E')

    if py3:
        strio = BytesIO(raws.encode())
    else:
        strio = StringIO(raws)
    darr = np.genfromtxt(strio,delimiter=nfloat)

    nav= DataFrame(np.hstack((np.asarray(sv,int)[:,None],darr)), epoch,
               ['sv','SVclockBias','SVclockDrift','SVclockDriftRate','IODE',
                'Crs','DeltaN','M0','Cuc','Eccentricity','Cus','sqrtA','TimeEph',
                'Cic','OMEGA','CIS','Io','Crc','omega','OMEGA DOT','IDOT',
                'CodesL2','GPSWeek','L2Pflag','SVacc','SVhealth','TGD','IODC',
                'TransTime','FitIntvl'])

    return nav

if __name__ == '__main__':
    from argparse import ArgumentParser
    p = ArgumentParser(description='example of reading a RINEX 2 Navigation file')
    p.add_argument('navfn',help='path to RINEX Navigation file',type=str)
    p = p.parse_args()

    nav = readRINEXnav(p.navfn)
    print(nav.head())
