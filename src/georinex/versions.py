import xarray
import numpy
import sys
import pandas
from . import __version__

print("Georinex", __version__)
print("Python", sys.version, sys.platform)
print("xarray", xarray.__version__)
print("Numpy", numpy.__version__)
print("Pandas", pandas.__version__)

try:
    import pytest

    print("Pytest", pytest.__version__)
except ImportError:
    pass
