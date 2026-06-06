import pandas as pd


def janobs(file_path):
    df = pd.read_csv(file_path, sep='|', header=None)
    df.columns = ["lines"]
    i_end_of_header = df[df.lines.str.contains('END OF HEADER')].index[0]
    header = df.iloc[:i_end_of_header]
    df = df.iloc[i_end_of_header + 1:].reset_index(drop=True)
    df["i"] = df.index
    is_timestamp = df.lines.str.startswith('>')
    timestamps = df[df.lines.str.startswith('>')]
    timestamps['rx_time'] = pd.to_datetime(timestamps.lines.str[2:29], format="%Y %m %d %H %M %S.%f")
    timestamps = timestamps.drop(columns='lines')
    df = pd.merge_asof(df, timestamps, on='i', direction='backward').drop(columns='i')[~is_timestamp]
    df = df[~is_timestamp]
    df.columns = ["records", "timestamps"]
    df["sv"] = df.records.str[:3]
    ...
