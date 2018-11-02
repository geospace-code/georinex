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
        return 'GPS'
    elif file_type == 'R':
        return 'GLO'
    elif file_type == 'E':
        return 'GAL'
    elif file_type == 'J':
        return 'QZS'
    elif file_type == 'C':
        return 'BDT'
    elif file_type == 'I':
        return 'IRN'

    # Else the type is mixed and the time system must be specified in
    # TIME OF FIRST OBS row.
    return header['TIME OF FIRST OBS'][48:51]
