@echo off

rem  batch program : RNX2CRZ.bat
rem        created  by HATANAKA, Y.  19/Dec/1996
rem        modified by HATANAKA, Y.  02/Jul/2009
rem        e-mail: hata@gsi.go.jp
rem  RINEX file compression
rem  *** wildcard can be used ***
rem
rem  RINEX OBS file (*.??[oy]) --- CompactRINEX --- compress (*.??e)
rem  CompactRINEX                (*.??d)        --- compress (*.??e)
rem  RINEX NAV message file      (*.??n)        --- compress (*.??x)
rem  GLONASS NAV message file    (*.??g)        --- compress (*.??v)
rem  Galileo NAV message file    (*.??l)        --- compress (*.??t)
rem  Mixed GNSS NAV message file (*.??p)        --- compress (*.??q)
rem  SBAS NAV message file       (*.??h)        --- compress (*.??u)
rem  SBAS Broadcast file         (*.??b)        --- compress (*.??a)
rem  RINEX MET file              (*.??m)        --- compress (*.??w)
rem  Clock file                  (*.??c)        --- compress (*.??k)
rem  compress RINEX files

for %%f in (%1) do call rnx2crz1 %%f

