[![Build Status](https://travis-ci.org/scienceopen/rinex-reader-python.svg?branch=master)](https://travis-ci.org/scienceopen/rinex-reader-python)
[![Coverage Status](https://coveralls.io/repos/scienceopen/rinex-reader-python/badge.svg)](https://coveralls.io/r/scienceopen/rinex-reader-python)

# rinex-reader-python
RINEX reader in Python -- reads NAV and OBS files

## Usage:
```
python RinexNavReader.py myrinex.XXn
python RinexObsReader.py myrinex.XXo
```


### RINEX OBS reader algorithm:
1. read overall OBS header (so we know what to expect in the rest of the OBS file)
2. preallocate pandas 3D Panel to fit all data -- this is a key difference from other software out there, that repetitively reallocates memory via appending and gets very very slow.  The Panel is a self-describing variable, each axis has text indices.
3. fill the 3D Panel with the data by reading in blocks -- another key difference from other programs out there, instead of reading character by character I ingest a whole time step of text at once, helping keep the processing closer to CPU cache making it much faster. 
