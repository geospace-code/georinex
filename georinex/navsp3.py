#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sat Jul 13 14:50:28 2019

@author: smrak
"""

import xarray
import numpy as np
from datetime import datetime

def sp3(f):
    with open(f, 'r') as F:
        # Read in the context
        sp3 = F.readlines()[:-1] #22
        # Number of active satellites
        svnumline = sp3[2]
        svnum = int(svnumline.split()[1])
        skip = svnum + 1
        # Skip header
        sp3 = sp3[22:]
        # Paramter initialization
        svlist = np.array([l[1:4] for l in sp3[1:skip]])
        ecef = np.nan * np.ones((svlist.size,len(sp3[::skip]), 3), dtype=np.float32)
        clock = np.nan * np.ones((svlist.size, len(sp3[::skip])), dtype=np.float32)
        # Read in data
        # 1) Time
        navtimes = np.array([datetime.strptime(l.strip('\n')[3:-2], "%Y %m %d %H %M %S.%f") for l in sp3[::skip]], dtype='datetime64[s]')
        for i, sv in enumerate(svlist):
            sp3 = sp3[1:]
            for j in range(navtimes.size):
                ecef[i,j,:] = np.array([x for x in sp3[::skip][j][4:-1].lstrip().rstrip().split(' ') if x][:3], dtype=np.float32)
                clock[i,j] = np.float32(sp3[::skip][0][47:60])
    F.close()

    nav = xarray.Dataset(coords={'time': navtimes, 'sv': svlist, 'xyz' : ['ecefx', 'ecefy', 'ecefz']})
    nav['ecef'] = (('sv', 'time', 'xyz'), ecef)
    nav['clock'] = (('sv', 'time'), clock)
    
    return nav