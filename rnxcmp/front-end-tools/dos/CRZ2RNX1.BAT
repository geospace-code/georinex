@echo off

rem  batch program : CRZ2RNX1.bat 
rem        created  by HATANAKA, Y.  19/Dec/1996
rem        modified by HATANAKA, Y.  02/Jul/2009
rem        e-mail: hata@gsi.go.jp
rem  RINEX file recovery
rem  uncompress and/or recover RINEX file
rem  *** Only 1 file can be processed ***
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
rem
rem  %1 filename

splname %1 > SPL_NAME.BAT
call SPL_NAME.BAT
del  SPL_NAME.BAT

if %last%==d goto CRX
if %last%==D goto CRX
if %last%==e goto CRZ
if %last%==E goto CRZ
if %last%==y goto ZRX
if %last%==Y goto ZRX
if %last%==x goto NAV
if %last%==X goto NAV
if %last%==v goto GLO
if %last%==V goto GLO
if %last%==t goto GAL
if %last%==T goto GAL
if %last%==q goto MIX
if %last%==Q goto MIX
if %last%==u goto SNV
if %last%==U goto SNV
if %last%==a goto SBR
if %last%==A goto SBR
if %last%==w goto MET
if %last%==W goto MET
if %last%==k goto CLK
if %last%==K goto CLK

goto EXIT

:CRX
    crx2rnx %1 -f
    goto EXIT

:CRZ
    copy %base%e %base%z > nul:
    call decompr %base%z %base%d
    crx2rnx %base%d -f
    del %base%z
    del %base%d
    goto EXIT

:ZRX
    copy %base%y %base%z > nul:
    call decompr %base%z %base%o
    del %base%z
    goto EXIT

:NAV
    copy %base%x %base%z > nul:
    call decompr %base%z %base%n
    del  %base%z
    goto EXIT

:GLO
    copy %base%v %base%z > nul:
    call decompr %base%z %base%g
    del  %base%z
    goto EXIT

:GAL
    copy %base%t %base%z > nul:
    call decompr %base%z %base%l
    del  %base%z
    goto EXIT

:MIX
    copy %base%q %base%z > nul:
    call decompr %base%z %base%b
    del  %base%z
    goto EXIT

:SNV
    copy %base%u %base%z > nul:
    call decompr %base%z %base%h
    del  %base%z
    goto EXIT

:SBR
    copy %base%a %base%z > nul:
    call decompr %base%z %base%b
    del  %base%z
    goto EXIT

:MET
    copy %base%w %base%z > nul:
    call decompr %base%z %base%m
    del  %base%z
    goto EXIT

:CLK
    copy %base%k %base%z > nul:
    call decompr %base%z %base%c
    del  %base%z
    goto EXIT

:EXIT
