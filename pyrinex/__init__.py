from pathlib import Path
import logging
import xarray
from time import time
import numpy as np
from typing import Union
#
from .rinex2 import _rinexnav2, _scan2
from .rinex3 import _rinexnav3, _scan3

COMPLVL = 1  # for NetCDF compression. too high slows down with little space savings.

def readrinex(rinexfn:Path, outfn:Path=None, use:Union[str,list,tuple]=None, verbose:bool=True) -> xarray.Dataset:
    nav = None
    obs = None
    rinexfn = Path(rinexfn).expanduser()

    fnl = rinexfn.name.lower()
    if fnl.endswith('n') or fnl.endswith('n.rnx'):
        nav = rinexnav(rinexfn, outfn)
    elif fnl.endswith('o') or fnl.endswith('o.rnx'):
        obs = rinexobs(rinexfn, outfn, use=use, verbose=verbose)
    elif rinexfn.suffix.endswith('.nc'):
        nav = rinexnav(rinexfn)
        obs = rinexobs(rinexfn)
    else:
        raise ValueError("I dont know what type of file you're trying to read: {}".format(rinexfn))

    return obs,nav


def getRinexVersion(fn:Path) -> float:
    fn = Path(fn).expanduser()

    with fn.open('r') as f:
        """verify RINEX version"""
        line = f.readline()
        return float(line[:9])

#%% Navigation file
def rinexnav(fn:Path, ofn:Path=None, group:str='NAV') -> xarray.Dataset:

    fn = Path(fn).expanduser()
    if fn.suffix=='.nc':
        try:
            return xarray.open_dataset(fn, group=group)
        except OSError:
            logging.error('Group {} not found in {}'.format(group,fn))
            return

    ver = getRinexVersion(fn)
    if int(ver) == 2:
        nav =  _rinexnav2(fn)
    elif int(ver) == 3:
        nav = _rinexnav3(fn)
    else:
        raise ValueError('unknown RINEX verion {}  {}'.format(ver,fn))

    if ofn:
        ofn = Path(ofn).expanduser()
        print('saving NAV data to',ofn)
        wmode='a' if ofn.is_file() else 'w'
        nav.to_netcdf(ofn, group=group, mode=wmode)

    return nav

# %% Observation File
def rinexobs(fn:Path, ofn:Path=None, use:Union[str,list,tuple]=None,
             group:str='OBS',verbose:bool=False) -> xarray.Dataset:
    """
    Program overviw:
    1) scan the whole file for the header and other information using scan(lines)
    2) each epoch is read

    rinexobs() returns the data in an xarray.Dataset
    """

    fn = Path(fn).expanduser()
    if fn.suffix=='.nc':
        try:
            return xarray.open_dataset(fn, group=group)
        except OSError:
            logging.error('Group {} not found in {}'.format(group,fn))
            return



    tic = time()
    ver = getRinexVersion(fn)
    if int(ver) == 2:
        obs = _scan2(fn, use, verbose)
    elif int(ver) == 3:
        if use is None or isinstance(use,str):
            obs = _scan3(fn, use, verbose)
        elif isinstance(use,(tuple,list,np.ndarray)):
            if len(use) == 1:
                obs = _scan3(fn, use[0], verbose)
            else:
                obs = {}
                for u in use:
                    obs[u] = _scan3(fn, u, verbose)
    else:
        raise ValueError('unknown RINEX verion {}  {}'.format(ver,fn))
        print("finished in {:.2f} seconds".format(time()-tic))


    if ofn:
        ofn = Path(ofn).expanduser()
        print('saving OBS data to',ofn)
        wmode='a' if ofn.is_file() else 'w'


        if isinstance(obs,xarray.Dataset):
            enc = {k:{'zlib':True,'complevel':COMPLVL,'fletcher32':True} for k in obs.data_vars}
            obs.to_netcdf(ofn, group=group, mode=wmode,encoding=enc)
        elif isinstance(obs,dict):
            for k,v in obs.items():
                enc = {k:{'zlib':True,'complevel':COMPLVL,'fletcher32':True} for k in v.data_vars}
                name = k+'-'+ofn.name
                obs[k].to_netcdf(ofn.parent/name,group=group,mode=wmode,encoding=enc)

    return obs


