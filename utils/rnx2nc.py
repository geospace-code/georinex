#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jul  4 13:25:38 2017

@author: Sebastijan Mrak <smrak@gmail.com>
"""
import os
import glob
import platform
from time import sleep
import georinex as gr

def _convert(file, odir, i):
    print ('Converting file: ', file)
    try:
        gr.load(file, out=odir, useindicators=i)
    except Exception as e:
        print (e)
    sleep(0.1)
    
def _iterate(file, odir, override, i):
    head, tail = os.path.split(file)
    rx = tail[0:8]
    print (rx)
    if platform.system() == 'Linux':
        newfn = odir + '/' + rx + '.nc'
    elif platform.system() == 'Windows':
        newfn = odir + '\\' + rx + '.nc'
    if not override:
        if not os.path.exists(newfn):
            _convert(file, odir,i)
    else:
        _convert(file, odir,i)
        
def convertObs2HDF(folder=None, sufix=None, odir=None, override=False,i=False):
    """
    This script converts RINEX 2.11 observation files in a given directory into
    a hdf5 organized data structure, utilizing pyRINEX script. Find the script
    in the main directory.
    """
    if os.path.isdir(folder):
        if sufix is None:
            wlist = ['*.**o']
        else:
            wlstr = sufix
        if odir is None:
            odir = folder
        for wlstr in wlist:
            filestr = os.path.join(folder,wlstr)
            flist = sorted(glob.glob(filestr))
            for file in flist:
                _iterate(file, odir, override, i)
    elif os.path.isfile(folder):
        print (folder)
        if folder[-1] == 'o' or folder[-1] == 'O' or folder[-1] == 'd': # Very stupid / change to match OBS file template
            file = folder
            if odir is None:
                odir, filename = os.path.split(folder)
            _iterate(file, odir, override, i)
        else:
            print ('Not a RInex OBS file (.**o)')
    else:
        print ("Something went wrong, dude")
                    
if __name__ == '__main__':
    from argparse import ArgumentParser
    p = ArgumentParser()
    p.add_argument('folder',type=str)
    p.add_argument('-odir', '--odir', help='Destination folder, if None-> the same as input folder', default=None)
    p.add_argument('-f', '--force', help="Force override, if the NC file already exist", action='store_true')
    p.add_argument('-i', '--indicators', help="Parse & store the indicators (lli/ssi)?", action='store_true')
    p.add_argument('-s', '--sufix', help='specify a sufix for desired observation files', type=str, default=None)
    P = p.parse_args()
    
    convertObs2HDF(folder = P.folder, sufix=P.sufix, odir=P.odir, override=P.force, i=P.indicators)