# NAV RINEX files

To read a RINEX 2 or 3 NAV file:

```python
nav = gr.load('tests/demo_MN.rnx')
```

Returns an
[xarray.Dataset](http://xarray.pydata.org/en/stable/api.html#dataset)
of the data within the RINEX 3 or RINEX 2 Navigation file.
Indexed by time x quantity

## Indexing

Assume the NAV data is loaded in variable `nav`.
Select satellite(s) (here, `G13`) by

```python
nav.sel(sv='G13')
```

Pick any parameter (say, `M0`) across all satellites and time (or index by that first) by:

```python
nav['M0']
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

The "times" variable is the Epoch / ToC (Time of Clock).
