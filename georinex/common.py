from pathlib import Path
try:
    import psutil
except ImportError:
    psutil = None


def rinex_string_to_float(x: str) -> float:
    return float(x.replace('D', 'E'))


def check_ram(memneed: int, fn: Path):
    if psutil is None:
        return

    mem = psutil.virtual_memory()

    if memneed > 0.5*mem.available:  # because of array copy Numpy => Xarray
        raise RuntimeError(f'{fn} needs {memneed/1e9} GBytes RAM, but only {mem.available/1e9} Gbytes available \n'
                           'try fast=False to reduce RAM usage, raise a GitHub Issue to let us help')


def determine_time_system(header: dict) -> str:
    """Determine which time system is used in an observation file."""
    # Current implementation is quite inconsistent in terms what is put into
    # header.
    try:
        file_type = header['RINEX VERSION / TYPE'][40]
    except KeyError:
        file_type = header['systems']

    if file_type == 'G':
        ts = 'GPS'
    elif file_type == 'R':
        ts = 'GLO'
    elif file_type == 'E':
        ts = 'GAL'
    elif file_type == 'J':
        ts = 'QZS'
    elif file_type == 'C':
        ts = 'BDT'
    elif file_type == 'I':
        ts = 'IRN'
    elif file_type == 'M':
        # Else the type is mixed and the time system must be specified in
        # TIME OF FIRST OBS row.
        ts = header['TIME OF FIRST OBS'][48:51]
    else:
        raise ValueError(f'unknown file type {file_type}')

    return ts
