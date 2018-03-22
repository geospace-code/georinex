from . import Path
import numpy as np
from datetime import datetime
from io import BytesIO
import xarray
#
STARTCOL2 = 3 #column where numerical data starts for RINEX 2

F = ('SVclockBias','SVclockDrift','SVclockDriftRate','IODE','Crs','DeltaN',
     'M0','Cuc','Eccentricity','Cus','sqrtA','Toe','Cic','omega0','Cis','Io',
     'Crc','omega','OmegaDot','IDOT','CodesL2','GPSWeek','L2Pflag','SVacc',
     'SVhealth','TGD','IODC','TransTime','FitIntvl')

def _rinexnav2(fn, ofn=None):
    """
    Reads RINEX 2.11 NAV files
    Michael Hirsch, Ph.D.
    SciVision, Inc.

    http://gage14.upc.es/gLAB/HTML/GPS_Navigation_Rinex_v2.11.html
    ftp://igs.org/pub/data/format/rinex211.txt
    """
    fn = Path(fn).expanduser()

    Nl = 7 #number of additional lines per record, for RINEX 2 NAV
    Nf = 29 # number of fields per record, for RINEX 2 NAV
    assert len(F) == 29
    Lf = 19 # string length per field

    sv = []; epoch=[]; raws=[]

    with fn.open('r') as f:
        """verify RINEX version, and that it's NAV"""
        line = f.readline()
        ver = float(line[:9])
        assert int(ver)==2,'see _rinexnav3() for RINEX 3.0 files'
        assert line[20] == 'N', 'Did not detect Nav file'

        """
        skip header, which has non-constant number of rows
        """
        while True:
            if 'END OF HEADER' in f.readline():
                break
        """
        now read data
        """
        for l in f:
            # format I2 http://gage.upc.edu/sites/default/files/gLAB/HTML/GPS_Navigation_Rinex_v2.11.html
            sv.append(int(l[:2]))
            # format I2
            year = int(l[3:5])  # yes, skipping one unused columsn
            if 80 <= year <=99:
                year += 1900
            elif year<80: #good till year 2180
                year += 2000

            epoch.append(datetime(year =year,
                                  month   =int(l[6:8]),
                                  day     =int(l[9:11]),
                                  hour    =int(l[12:14]),
                                  minute  =int(l[15:17]),
                                  second  =int(l[17:20]),  # python reads second and fraction in parts
                                  microsecond=int(l[21])*100000))
            """
            now get the data as one big long string per SV
            """
            raw = l[22:79]  # NOTE: MUST be 79, not 80 due to some files that put \n a character early!
            for _ in range(Nl):
                raw += f.readline()[STARTCOL2:79]
            # one line per SV
            raws.append(raw.replace('D','E'))
# %% parse
    # for RINEX 2, don't use delimiter
    darr = np.empty((len(raws), Nf))

    for i,r in enumerate(raws):
        darr[i,:] = np.genfromtxt(BytesIO(r.encode('ascii')), delimiter=[Lf]*Nf)  # must have *Nf to avoid false nan on trailing spaces

    dsf = {f: ('time',d) for (f,d) in zip(F,darr.T)}
    dsf.update({'sv':('time',sv)})

    nav = xarray.Dataset(dsf,
                          coords={'time':epoch},
                          attrs={'RINEX version':ver,
                                 'RINEX filename':fn.name}
                          )


    if ofn:
        ofn = Path(ofn).expanduser()
        print('saving NAV data to',ofn)
        if ofn.is_file():
            wmode='a'
        else:
            wmode='w'
        nav.to_netcdf(ofn, group='NAV', mode=wmode)

    return nav
