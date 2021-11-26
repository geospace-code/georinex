# RINEX OBS files

To read RINEX 2 or 3 OBS file:

```python
obs = gr.load('tests/demo_MO.rnx')
```

This returns an
[xarray.Dataset](http://xarray.pydata.org/en/stable/api.html#dataset)
of data within the RINEX observation file.

NaN is used as a filler value, so the commands typically end with
.dropna(dim='time',how='all') to eliminate the non-observable data vs
time. As per pg. 15-20 of RINEX 3.03
[specification](ftp://igs.org/pub/data/format/rinex303.pdf),
only certain fields are valid for particular satellite systems.
Not every receiver receives every type of GNSS system.
Most Android devices in the Americas receive at least GPS and GLONASS.

## Header

Get a `dict()` of the RINEX file header:

```python
hdr = gr.rinexheader('myfile.rnx')
```

## Indexing

assume the OBS data from a file is loaded in variable `obs`.

Select satellite(s) (here, `G13`)

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

loads only Galileo data by the parameter E.
`python -m georinex.read` allow this to be specified as the -use command line parameter.

If however you want to do this after loading all the data anyway, you can make a Boolean indexer

```python
Eind = obs.sv.to_index().str.startswith('E')  # returns a simple Numpy Boolean 1-D array
Edata = obs.isel(sv=Eind)  # any combination of other indices at same time or before/after also possible
```

Uses speculative time preallocation `gr.load(..., fast=True)` by default.
Set `fast=False` or CLI option `python -m georinex.read -strict` to fall back to double-read strict (slow) preallocation.
Please open a GitHub issue if this is a problem.

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

## Plot

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

## Read times

Print start, stop times and measurement interval:

```sh
python -m georinex.time ~/my.rnx
```

Print start, stop times and measurement interval for all files in a directory:

```sh
python -m georinex.time ~/data *.rnx
```

Get vector of `datetime.datetime` in RINEX file:

```python
times = gr.gettimes('~/my.rnx')
```
