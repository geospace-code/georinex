#!/usr/bin/env python
"""
for debugging, profiling. May not work right now.
"""

import cProfile
from pstats import Stats

profFN = "RinexObsReader.pstats"
cProfile.run("rinexobs(rinexfn)", profFN)
Stats(profFN).sort_stats("time", "cumulative").print_stats(20)
