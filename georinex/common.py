def rinex_string_to_float(x: str) -> float:
    return float(x.replace('D', 'E'))


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
