@echo off

rem  batch program : RNX2CRZ1.bat
rem        created  by HATANAKA, Y.  19/Dec/1996
rem        modified by HATANAKA, Y.  02/Jul/2009
rem        e-mail: hata@gsi.go.jp
rem  RINEX file compression
rem  *** Only 1 file can be processed ***
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
rem  uncompress and/or recover RINEX file
rem
rem  %1 filename

splname %1 > SPL_NAME.BAT
call SPL_NAME.BAT
del  SPL_NAME.BAT

if %last%==o goto OBS
if %last%==O goto OBS
if %last%==y goto ZOBS
if %last%==Y goto ZOBS
if %last%==d goto CRX
if %last%==D goto CRX
if %last%==n goto NAV
if %last%==N goto NAV
if %last%==g goto GLO
if %last%==G goto GLO
if %last%==l goto GAL
if %last%==L goto GAL
if %last%==p goto MIX
if %last%==P goto MIX
if %last%==h goto SNV
if %last%==H goto SNV
if %last%==b goto SBR
if %last%==B goto SBR
if %last%==m goto MET
if %last%==M goto MET
if %last%==c goto CLK
if %last%==C goto CLK
goto EXIT

:OBS
    rnx2crx %1 -f
    call compr %base%d %base%e
    del  %base%d
    goto EXIT

:ZOBS
    copy %1 %base%z > nul:
    call decompr %base%z %base%o
    del  %base%z
    rnx2crx %base%o -f
    call compr %base%d %base%e
    del  %base%d
    goto EXIT

:CRX
    call compr %1 %base%e
    goto EXIT

:NAV
    call compr %1 %base%x
    goto EXIT

:GLO
    call compr %1 %base%v
    goto EXIT

:GAL
    call compr %1 %base%t
    goto EXIT

:MIX
    call compr %1 %base%q
    goto EXIT

:SNV
    call compr %1 %base%u
    goto EXIT

:SBR
    call compr %1 %base%a
    goto EXIT

:MET
    call compr %1 %base%w
    goto EXIT

:CLK
    call compr %1 %base%k
    goto EXIT

:EXIT
