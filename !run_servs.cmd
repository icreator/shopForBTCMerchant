rem start ..\wallets--\!!start_wallets.cmd

rem set prog=web2py.py
set prog=web2py.exe
set app=shop2
set not_local=False
set interval=15
set interval60=60

timeout /t 10
start !run_serv_blocks.cmd %prog% %app% %not_local% %interval%
timeout /t 3
start !run_serv_notes.cmd %prog% %app% %not_local% %interval%


rem clear block_proc .locks!
cd ..\wallets--
@del /Q .lock_* >nul
cd ..\%app%

rem start servers

rem повтор тольк этого таска
:rep

..\..\%prog% -S %app% -M -R applications/%app%/modules/serv_rates.py -A %not_local% %interval60%

rem if fail - repeat
timeout /t 20
goto rep

pause