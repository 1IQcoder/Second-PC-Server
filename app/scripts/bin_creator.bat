@echo off
set "bin_folder=..\bin"
set "bat_name=spcs"

if not exist "%bin_folder%" mkdir "%bin_folder%"
set "bat_path="%bin_folder%\%bat_name%.bat""

echo @echo off > %bat_path%"
echo set "BAT_DIR=%%~dp0" >> %bat_path%
echo set "BAT_DIR=%%BAT_DIR:bin=cli%%" >> %bat_path%
echo set "BAT_DIR=%%BAT_DIR%%\cli.exe" >> %bat_path%
echo. >> %bat_path%
echo %%BAT_DIR%% %%* >> %bat_path%

