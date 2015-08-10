.. image:: https://codeclimate.com/github/scienceopen/pyrinex/badges/gpa.svg
  :target: https://codeclimate.com/github/scienceopen/pyrinex
  :alt: Code Climate
.. image:: https://travis-ci.org/scienceopen/pyrinex.svg?branch=master
  :target: https://travis-ci.org/scienceopen/pyrinex
.. image:: https://coveralls.io/repos/scienceopen/pyrinex/badge.svg?branch=master&service=github 
  :target: https://coveralls.io/github/scienceopen/pyrinex?branch=master

=======
PyRinex
=======

RINEX 2.1 reader in Python -- reads NAV and OBS files into Pandas 3-D Panel for easy use in analysis and plotting.

Writes to HDF5 (for couple order of magnitude speedup in reading and allows filtering/processing of gigantic files too large to fit into RAM).

RINEX 3 is in work, and NOT working yet.

=============
Installation
=============

.. code:: bash

  git clone --depth 1 https://github.com/scienceopen/pyrinex
  conda install --file requirements.txt

======
Usage
======

.. code:: bash

  python RinexNavReader.py myrinex.XXn
  python RinexObsReader.py myrinex.XXo

RINEX OBS reader algorithm
==========================
1. read overall OBS header (so we know what to expect in the rest of the OBS file)
2. preallocate pandas 3D Panel to fit all data -- this is a key difference from other software out there, that repetitively reallocates memory via appending.  The Panel is a self-describing variable, each axis has text indices.
3. fill the 3D Panel with the data by reading in blocks -- another key difference from other programs out there, instead of reading character by character I ingest a whole time step of text at once, helping keep the processing closer to CPU cache making it much faster. 
