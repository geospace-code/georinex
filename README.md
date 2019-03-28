[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.2580306.svg)](https://doi.org/10.5281/zenodo.2580306)
[![Travis CI](https://travis-ci.org/scivision/georinex.svg?branch=master)](https://travis-ci.org/scivision/georinex)
[![Coverage Status](https://coveralls.io/repos/github/scivision/georinex/badge.svg?branch=master)](https://coveralls.io/github/scivision/georinex?branch=master)
[![Build status](https://ci.appveyor.com/api/projects/status/rautwf0jrn4w5v6n?svg=true)](https://ci.appveyor.com/project/scivision/georinex)
[![PyPi versions](https://img.shields.io/pypi/pyversions/georinex.svg)](https://pypi.python.org/pypi/georinex)
[![PyPi Download stats](http://pepy.tech/badge/georinex)](http://pepy.tech/project/georinex)
[![Xarray badge](https://img.shields.io/badge/powered%20by-xarray-orange.svg?style=flat)](http://xarray.pydata.org/en/stable/why-xarray.html)

# GeoRinex

RINEX 3 and RINEX 2 reader and batch conversion to NetCDF4 / HDF5 in Python or Matlab.
Batch converts NAV and OBS GPS RINEX (including Hatanaka compressed OBS) data into
[xarray.Dataset](http://xarray.pydata.org/en/stable/api.html#dataset)
for easy use in analysis and plotting.
This gives remarkable speed vs. legacy iterative methods, and allows for HPC / out-of-core operations on massive amounts of GNSS data.
GeoRinex works in Python &ge; 3.6 and has over 125 unit tests driven by Pytest.

Pure compiled language RINEX processors such as within Fortran NAPEOS give perhaps 2x faster performance than this Python program--that's pretty good for a scripted language like Python!
However, the initial goal of this Python program was to be for one-time offline conversion of ASCII (and compressed ASCII) RINEX to HDF5/NetCDF4,
where ease of cross-platform install and correctness are primary goals.

![RINEX plot](tests/example_plot.png)


## Inputs

* RINEX 3.x or RINEX 2.x
  * NAV
  * OBS
* Plain ASCII or seamlessly read compressed ASCII in:
  * `.gz` GZIP
  * `.Z` LZW
  * `.zip`
* Hatanaka compressed RINEX (plain `.crx` or `.crx.gz` etc.)
* Python `io.StringIO` text stream RINEX

## Output

* File: NetCDF4 (subset of HDF5), with `zlib` compression.
This yields orders of magnitude speedup in reading/converting RINEX data and allows filtering/processing of gigantic files too large to fit into RAM.
* In-memory: Xarray.Dataset. This allows all the database-like indexing power of Pandas to be unleashed.

## Install

Latest stable release:
```sh
pip install georinex
```

Current development version:
```sh
git clone https://github.com/scivision/georinex

cd georinex

python -m pip install -e .
```

### Optional Hatanaka
If you need to use `.crx` Hatanaka compressed RINEX, compile the `crx2rnx` code by:
```sh
make install -C rnxcmp
```

#### Windows
For optional Hatanaka converter on Windows, assuming you have
[installed MinGW compiler on Windows](https://www.scivision.co/windows-gcc-gfortran-cmake-make-install/):
```posh
set CC=gcc
mingw32-make -C rnxcmp
```

Currently, `unlzw` doesn't work on Windows, making `.Z` files unreadable.

### Selftest

It can be useful to check the setup of your system with:
```sh
python -m pytest
```

```
155 passed, 1 skipped
```


## Usage

The simplest command-line use is through the top-level `ReadRinex` script.
Normally you'd use the `-p` option with single files to plot, if not converting.

* Read single RINEX3 or RINEX 2 Obs or Nav file:
  ```sh
  ReadRinex myrinex.XXx
  ```
* Read NetCDF converted RINEX data:
  ```sh
  ReadRinex myrinex.nc
  ```
* Batch convert RINEX to NetCDF4 / HDF5 (this example for RINEX 2 OBS):
  ```sh
  rnx2hdf5 ~/data "*o" -o ~/data
  ```
  in this example, the suffix `.nc` is appended to the original RINEX filename: `my.15o` => `my.15o.nc`

By default all plots and status messages are off, unless using the `-p` option to save processing time.

It's suggested to save the GNSS data to NetCDF4 (a subset of HDF5) with the `-o`option,
as NetCDF4 is also human-readable, yet say 1000x faster to load than RINEX.

You can also of course use the package as a python imported module as in
the following examples. Each example assumes you have first done:

```python
import georinex as gr
```

Uses speculative time preallocation `gr.load(..., fast=True)` by default.
Set `fast=False` or `ReadRinex.py -strict` to fall back to double-read strict (slow) preallocation.
Please open a GitHub issue if this is a problem.

### Time limits
Time bounds can be set for reading -- load only data between those time bounds with the
```sh
--tlim start stop
```
option, where `start` and `stop` are formatted like `2017-02-23T12:00`

```python
dat = gr.load('my.rnx', tlim=['2017-02-23T12:59', '2017-02-23T13:13'])
```

### Measurement selection
Further speed increase can arise from reading only wanted measurements:
```sh
--meas C1C L1C
```


```python
dat = gr.load('my.rnx', meas=['C1C', 'L1C'])
```

### Use Signal and Loss of Lock indicators
By default, the SSI and LLI (loss of lock indicators) are not loaded to speed up the program and save memory.
If you need them, the `-useindicators` option loads SSI and LLI for OBS 2/3 files.


## read RINEX

This convenience function reads any possible format (including compressed, Hatanaka) RINEX 2/3 OBS/NAV or `.nc` file:

```python
obs = gr.load('tests/demo.10o')
```


### read times in OBS, NAV file(s)
Print start, stop times and measurement interval in a RINEX OBS or NAV file:
```sh
TimeRinex ~/my.rnx
```

Print start, stop times and measurement interval for all files in a directory:
```sh
TimeRinex ~/data *.rnx
```

Get vector of `datetime.datetime` in RINEX file:
```python
times = gr.gettimes('~/my.rnx')
```

## read Obs

If you desire to specifically read a RINEX 2 or 3 OBS file:

```python
obs = gr.load('tests/demo_MO.rnx')
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


### read OBS header
To get a `dict()` of the RINEX file header:
```python
hdr = gr.rinexheader('myfile.rnx')
```

### Index OBS data

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
import georinex as gr
obs = gr.load('myfile.o', use='E')
```
would load only Galileo data by the parameter E.
`ReadRinex` allow this to be specified as the -use command line parameter.

If however you want to do this after loading all the data anyway, you can make a Boolean indexer
```python
Eind = obs.sv.to_index().str.startswith('E')  # returns a simple Numpy Boolean 1-D array
Edata = obs.isel(sv=Eind)  # any combination of other indices at same time or before/after also possible
```

###  Plot OBS data

Plot for all satellites L1C:
```python
from matplotlib.pyplot import figure, show
ax = figure().gca()
ax.plot(obs.time, obs['L1C'])
show()
```

Suppose L1C pseudorange plot is desired for `G13`:
```python
obs['L1C'].sel(sv='G13').dropna(dim='time',how='all').plot()
```

## read Nav


If you desire to specifically read a RINEX 2 or 3 NAV file:
```python
nav = gr.load('tests/demo_MN.rnx')
```

This returns an `xarray.Dataset` of the data within the RINEX 3 or RINEX 2 Navigation file.
Indexed by time x quantity


### Index NAV data

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
A significant reason for using `xarray` as the base class of GeoRinex is that big data operations are fast, easy and efficient.
It's suggested to load the original RINEX files with the `-use` or `use=` option to greatly speed loading and conserve memory.

A copy of the processed data can be saved to NetCDF4 for fast reloading and out-of-core processing by:
```python
obs.to_netcdf('process.nc', group='OBS')
```
`georinex.__init.py__` shows examples of using compression and other options if desired.

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

### Receiver location
While `APPROX LOCATION XYZ` gives ECEF location in RINEX OBS files, this is OPTIONAL for moving platforms.
If available, the `location` is written to the NetCDF4 / HDF5 output file on conversion.
To convert ECEF to Latitude, Longitude, Altitude or other coordinate systems, use
[PyMap3d](https://github.com/scivision/pymap3d).

Read location from NetCDF4 / HDF5 file can be accomplished in a few ways:

* using `PlotRXlocation.py` script, which loads and plots all RINEX and .nc files in a directory
* using `xarray`
  ```python
  obs = xarray.open_dataset('my.nc)

  ecef = obs.position
  latlon = obs.position_geodetic  # only if pymap3d was used
  ```
* Using `h5py`:
  ```python
  with h5py.File('my.nc') as f:
      ecef = h['OBS'].attrs['position']
      latlon = h['OBS'].attrs['position_geodetic']
  ```

## Converting to Pandas DataFrames
Although Pandas DataFrames are 2-D, using say `df = nav.to_dataframe()` will result in a reshaped 2-D DataFrame.
Satellites can be selected like `df.loc['G12'].dropna(0, 'all')` using the usual
[Pandas Multiindexing methods](http://pandas.pydata.org/pandas-docs/stable/advanced.html).

## Benchmark

An Intel Haswell i7-3770 CPU with plain uncompressed RINEX 2 OBS processes in about:
* [6 MB file](ftp://data-out.unavco.org/pub/rinex/obs/2018/021/ab140210.18o.Z): 5 seconds
* [13 MB file](ftp://data-out.unavco.org/pub/rinex/obs/2018/021/ab180210.18o.Z): 10 seconds

This processing speed is about within a factor of 2 of compiled RINEX parsers, with the convenience of Python, Xarray, Pandas and HDF5 / NetCDF4.

OBS2 and NAV2 currently have the fast pure Python read that has C-like speed.

### Obs3
OBS3 / NAV3 are not yet updated to new fast pure Python method.

Done on 5 year old Haswell laptop:
```sh
time ./ReadRinex.py tests/CEDA00USA_R_20182100000_23H_15S_MO.rnx.gz -u E
```

> real 48.6 s

```sh
time ./ReadRinex.py tests/CEDA00USA_R_20182100000_23H_15S_MO.rnx.gz -u E -m C1C
```

> real 17.6 s

### Profiling
using
```sh
conda install line_profiler
```
and `ipython`:
```ipython
%load_ext line_profiler

%lprun -f gr.obs3._epoch gr.load('tests/CEDA00USA_R_20182100000_23H_15S_MO.rnx.gz', use='E', meas='C1C')
```
shows that `np.genfromtxt()` is consuming about 30% of processing time, and `xarray.concat` and xarray.Dataset` nested inside `concat` takes over 60% of time.



## Notes

* RINEX 3.03 specification: ftp://igs.org/pub/data/format/rinex303.pdf
* RINEX 3.04 specification (Dec 2018): ftp://igs.org/pub/data/format/rinex304.pdf
* RINEX 3.04 release notes:  ftp://igs.org/pub/data/format/rinex304-release-notes.pdf


-   GPS satellite position is given for each time in the NAV file as
    Keplerian parameters, which can be
    [converted to ECEF](https://ascelibrary.org/doi/pdf/10.1061/9780784411506.ap03).
-   <https://downloads.rene-schwarz.com/download/M001-Keplerian_Orbit_Elements_to_Cartesian_State_Vectors.pdf>
-   <http://www.gage.es/gFD>

### Number of SVs visible
With the GNSS constellations in 2018, per the
[Trimble Planner](https://www.gnssplanning.com/)
the min/max visible SV would be about:

* Maximum: ~60 SV maximum near the equator in Asia / Oceania with 5 degree elev. cutoff
* Minimum: ~6 SV minimum at poles with 20 degree elev. cutoff and GPS only


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

UNAVCO [site map](https://www.unavco.org/instrumentation/networks/map/map.html#/): identify the 4-letter callsign of a station, and look in the FTP sites below for data from a site.

UNAVCO RINEX 3 data:

* OBS: ftp://data-out.unavco.org/pub/rinex3/obs/
* NAV: ftp://data-out.unavco.org/pub/rinex3/nav/

UNAVCO RINEX 2 data:

* OBS: ftp://data-out.unavco.org/pub/rinex/obs/
* NAV: ftp://data-out.unavco.org/pub/rinex/nav/


### Hatanaka compressed RINEX .crx
The compressed Hatanaka `.crx` or `.crx.gz` files are supported seamlessly via `crx2rnx` as noted in the Install section.
There are distinct from the supported `.rnx`, `.gz`, or `.zip` RINEX files.

Hatanaka, Y. (2008), A Compression Format and Tools for GNSS Observation
          Data, Bulletin of the Geospatioal Information Authority of Japan, 55, 21-30.
(available at http://www.gsi.go.jp/ENGLISH/Bulletin55.html)
