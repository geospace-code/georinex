try
    from pathlib import Path
    Path().expanduser() #fails python<3.5
except (ImportError,AttributeError):
    from pathlib2 import Path

