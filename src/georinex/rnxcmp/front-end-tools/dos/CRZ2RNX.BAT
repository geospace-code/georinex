@echo off

rem  batch program : CRZ2RNX.bat
rem        created  by HATANAKA, Y.  19/Dec/1996
rem        modified by HATANAKA, Y.  02/Jul/2009
rem        e-mail: hata@gsi.go.jp
rem  *** wildcard can be used ***
rem
rem  CompactRINEX(*.??d)                --- RINEX OBS file              (*.??o)
rem  compressed file (*.??e) --- CompactRINEX(*.??d) --- RINEX OBS file (*.??o)
rem  compressed file (*.??x)            --- RINEX NAV file              (*.??n)
rem  compressed file (*.??v)            --- GLONASS NAV message file    (*.??g)
rem  compressed file (*.??t)            --- Galileo NAV message file    (*.??l)
rem  compressed file (*.??q)            --- Mixed GNSS NAV message file (*.??p)
rem  compressed file (*.??u)            --- SBAS NAV message file       (*.??h)
rem  compressed file (*.??a)            --- SBAS Broadcast file         (*.??b)
rem  compressed file (*.??w)            --- RINEX MET file              (*.??m)
rem  compressed file (*.??k)            --- Clock file                  (*.??c)
rem  uncompress and/or recover RINEX file


for %%f in (%1) do call crz2rnx1 %%f

