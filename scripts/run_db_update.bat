@echo off
chcp 65001 >nul
REM wh40k-oracle three-source data refresh (BSData + MFM + downloads) + rebuild + aliases.
REM Registered as Windows Scheduled Task "wh40k-oracle-update". Runs unattended, logs to db_update.log.
cd /d %~dp0..

set HTTP_PROXY=http://127.0.0.1:7897
set HTTPS_PROXY=http://127.0.0.1:7897

echo ================================================================ >> db_update.log
echo [%DATE% %TIME%] db_compile update start >> db_update.log
.venv\Scripts\python.exe -m db_compile update >> db_update.log 2>&1
echo [%DATE% %TIME%] db_compile update exit code %ERRORLEVEL% >> db_update.log
