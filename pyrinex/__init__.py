try:
    from pathlib import Path
    Path().expanduser()
except (ImportError,AttributeError):
    from pathlib2 import Path

from .readRinexObs import *
from .readRinexNav import *