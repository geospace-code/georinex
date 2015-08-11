#!/usr/bin/env python3

from pyrinex.readRinexNav import readRinexNav
from pyrinex.readRinexObs import rinexobs

if __name__ == '__main__':
    from argparse import ArgumentParser
    p = ArgumentParser(description='example of reading a RINEX 2 Navigation file')
    p.add_argument('rinexfn',help='path to RINEX  file')
    p.add_argument('--h5',help='write data as HDF5',action='store_true')
    p.add_argument('--maxtimes',help='Choose to read only the first N INTERVALs of OBS file',type=int)
    p.add_argument('--profile',help='profile code for debugging',action='store_true')
    p = p.parse_args()

    rinexfn = p.rinexfn
    if rinexfn.lower().endswith('n'):
        nav = readRinexNav(rinexfn,p.h5)
        print(nav.head())
    elif rinexfn.lower().endswith('o'):
        if p.profile:
            import cProfile
            from pstats import Stats
            profFN = 'RinexObsReader.pstats'
            cProfile.run('rinexobs(rinexfn,p.h5,p.maxtimes)',profFN)
            Stats(profFN).sort_stats('time','cumulative').print_stats(20)
        else:
            blocks = rinexobs(rinexfn,p.h5,p.maxtimes)
    #%% plot
            try:
                import matplotlib.pyplot as plt
                plt.plot(blocks.items,blocks.ix[:,0,'P1'])
                plt.xlabel('time [UTC]')
                plt.ylabel('P1')
                plt.show()
            except Exception as e:
                print('skipped loading matplotlib (for selftest)  {}'.format(e))
    #%% TEC can be made another column (on the minor_axis) of the blocks Panel.
    else:
        print('** I dont know what type of file youre trying to read')