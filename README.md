[![Travis CI](https://travis-ci.org/scivision/pyrinex.svg?branch=master)](https://travis-ci.org/scivision/pyrinex)
[![coverage](https://coveralls.io/repos/scivision/pyrinex/badge.svg?branch=master&service=github)](https://coveralls.io/github/scivision/pyrinex?branch=master)
[![AppVeyor](https://ci.appveyor.com/api/projects/status/sxxqc77q7l3669dd?svg=true)](https://ci.appveyor.com/project/scivision/pyrinex)
[![PyPi versions](https://img.shields.io/pypi/pyversions/pyrinex.svg)](https://pypi.python.org/pypi/pyrinex)
[![PyPi wheels](https://img.shields.io/pypi/format/pyrinex.svg)](https://pypi.python.org/pypi/pyrinex)
[![Maintainability](https://api.codeclimate.com/v1/badges/69ce95c25db88777ed63/maintainability)](https://codeclimate.com/github/scivision/pyrinex/maintainability)
[![PyPi Download stats](http://pepy.tech/badge/pyrinex)](http://pepy.tech/project/pyrinex)
[![Xarray badge](https://img.shields.io/badge/powered%20by-xarray-orange.svg?style=flat)](http://xarray.pydata.org/en/stable/why-xarray.html)

# PyRinex

RINEX 3 and RINEX 2 reader in Python -- reads NAV and OBS GPS RINEX data
into
[xarray.Dataset](http://xarray.pydata.org/en/stable/api.html#dataset)
for easy use in analysis and plotting. This gives remarkable speed vs.
legacy iterative methods, and allows for HPC / out-of-core operations on
massive amounts of GNSS data.

Writes to NetCDF4 (subset of HDF5), with `zlib` compression. This is a
couple order of magnitude speedup in reading/converting RINEX data and
allows filtering/processing of gigantic files too large to fit into RAM.

Another key advantage of PyRinex is the Xarray base class, that allows
all the database-like indexing power of Pandas to be unleashed.

PyRinex works in Python &gt;= 3.6.

![RINEX plot](tests/example_plot.png)

## Install

    python -m pip install -e .

## Usage

The simplest command-line use is through the top-level `ReadRinex.py` script.

-   Read RINEX3 or RINEX 2 Obs or Nav file: `python ReadRinex.py myrinex.XXx`
-   Read NetCDF converted RINEX data: `python ReadRinex.py myrinex.nc`

It's suggested to save the GNSS data to NetCDF4 (a subset of HDF5) with the `-o`option,
as NetCDF4 is also human-readable, yet say 1000x faster to load than RINEX.

You can also of course use the package as a python imported module as in
the following examples. Each example assumes you have first done:

```python
import pyrinex as pr
```

### read Rinex

This convenience function reads any possible Rinex 2/3 OBS/NAV or .nc
file:

```python
obs,nav = pr.readrinex('tests/demo.10o')
```

### read Obs

If you desire to specifically read a RINEX 2 or 3 OBS file:

```python
obs = pr.rinexobs('tests/demo_MO.rnx')
```

This returns an
[xarray.Dataset](http://xarray.pydata.org/en/stable/api.html#dataset) of
data within the .XXo observation file.

NaN is used as a filler value, so the commands typically end with
.dropna(dim='time',how='all') to eliminate the non-observable data vs
time. As per pg. 15-20 of RINEX 3.03
[specification](ftp://igs.org/pub/data/format/rinex303.pdf), 
only certain fields are valid for particular satellite systems. 
Not every receiver receives every type of GNSS system. 
Most Android devices in the Americas receive at least GPS and GLONASS.

#### Index OBS data

assume the OBS data from a file is loaded in variable `obs`.

Select satellite(s) (here, `G13`) by
```python
obs.sel(sv='G13').dropna(dim='time',how='all')
```

Pick any parameter (say, `L1`) across all satellites and time (or index via `.sel()` by time and/or satellite too) by:
```python
obs['L1'].dropna(dim='time',how='all')
```

Indexing only a particular satellite system (here, Galileo) using Boolean indexing.
```python
import pyrinex as pr
obs = pr.rinexobs('myfile.o', use='E')
```
would load only Galileo data by the parameter E.
ReadRinex.py allow this to be specified as the -use command line parameter.

If however you want to do this after loading all the data anyway, you can make a Boolean indexer
```python
Eind = obs.sv.to_index().str.startswith('E')  # returns a simple Numpy boolean 1-D array
Edata = obs.isel(sv=Eind)  # any combination of other indices at same time or before/after also possible
```

####  Plot OBS data

Plot for all satellites L1C:
```python
from matplotlib.pyplot import figure, show
ax = figure().gca()
ax.plot(obs.time, obs['L1C'])
show()
```

Suppose L1C psuedorange plot is desired for `G13`:
```python
obs['L1C'].sel(sv='G13').dropna(dim='time',how='all').plot()
```

### read Nav


If you desire to specifically read a RINEX 2 or 3 NAV file:
```python
nav = pr.rinexnav('tests/demo_MN.rnx')
```

This returns an `xarray.Dataset` of the data within the RINEX 3 or RINEX 2 Navigation file.
Indexed by time x quantity


#### Index NAV data

assume the NAV data from a file is loaded in variable `nav`.
Select satellite(s) (here, `G13`) by
```python
nav.sel(sv='G13')
```

Pick any parameter (say, `M0`) across all satellites and time (or index by that first) by:
```python
nav['M0']
```

## Analysis 
A significant reason for using `xarray` as the base class of PyRinex is that big data operations are fast, easy and efficient. 
It's suggested to load the original RINEX files with the `-use` or `use=` option to greatly speed loading and convserve memory.

A copy of the processed data can be saved to NetCDF4 for fast reloading and out-of-core processing by:
```python
obs.to_netcdf('process.nc', group='OBS')
```
`pyrinex.__init.py__` shows examples of using compression and other options if desired.

### Join data from multiple files
Please see documentation for `xarray.concat` and `xarray.merge` for more details.
Assuming you loaded OBS data from one file into `obs1` and data from another file into `obs2`, and the data needs to be concatenated in time:
```python
obs = xarray.concat((obs1, obs2), dim='time')
```
The `xarray.concat`operation may fail if there are different SV observation types in the files. 
you can try the more general:
```python
obs = xarray.merge((obs1, obs2))
```

## Notes
 
RINEX 3.03 [specification](ftp://igs.org/pub/data/format/rinex303.pdf)

-   GPS satellite position is given for each time in the NAV file as
    Keplerian parameters, which can be 
    [converted to ECEF](https://ascelibrary.org/doi/pdf/10.1061/9780784411506.ap03).
-   <https://downloads.rene-schwarz.com/download/M001-Keplerian_Orbit_Elements_to_Cartesian_State_Vectors.pdf>
-   <http://www.gage.es/gFD>

### RINEX OBS reader algorithm

1.  read overall OBS header (so we know what to expect in the rest of the OBS file)
2.  fill the xarray.Dataset with the data by reading in blocks --
    another key difference from other programs out there, instead of
    reading character by character, I ingest a whole time step of text
    at once, helping keep the processing closer to CPU cache making it
    much faster.

### Data

For 
[capable Android devices](https://developer.android.com/guide/topics/sensors/gnss.html),
you can 
[log RINEX 3](https://play.google.com/store/apps/details?id=de.geopp.rinexlogger)
using the built-in GPS receiver.

Here is a lot of RINEX 3 data to work with:

-   [OBS data](ftp://data-out.unavco.org/pub/rinex3/obs/)
-   [NAV data](ftp://data-out.unavco.org/pub/rinex3/nav)

