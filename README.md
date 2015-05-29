[![Code Climate](https://codeclimate.com/github/scienceopen/pyrinex/badges/gpa.svg)](https://codeclimate.com/github/scienceopen/pyrinex)
[![Build Status](https://travis-ci.org/scienceopen/pyrinex.svg?branch=master)](https://travis-ci.org/scienceopen/pyrinex)
[![Coverage Status](https://coveralls.io/repos/scienceopen/pyrinex/badge.svg)](https://coveralls.io/r/scienceopen/pyrinex)

# PyRinex
RINEX 2.1 reader in Python -- reads NAV and OBS files
Writes to HDF5 (for couple order of magnitude speedup in reading and allows filtering/processing of gigantic files too large to fit into RAM).
RINEX 3 is in work, and NOT working yet.

Installation:
-------------
```
git clone --depth 1 https://scienceopen@github.com/scienceopen/pyrinex
```

Usage:
-------
```
python RinexNavReader.py myrinex.XXn
python RinexObsReader.py myrinex.XXo
```


### RINEX OBS reader algorithm:
1. read overall OBS header (so we know what to expect in the rest of the OBS file)
2. preallocate pandas 3D Panel to fit all data -- this is a key difference from other software out there, that repetitively reallocates memory via appending and gets very very slow.  The Panel is a self-describing variable, each axis has text indices.
3. fill the 3D Panel with the data by reading in blocks -- another key difference from other programs out there, instead of reading character by character I ingest a whole time step of text at once, helping keep the processing closer to CPU cache making it much faster. 
