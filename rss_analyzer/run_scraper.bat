@echo off
REM Wechsle in das Verzeichnis dieses Skripts
cd /d %~dp0

REM Falls Du ein virtuelles Environment nutzt, aktiviere es hier:
REM call venv\Scripts\activate

REM Starte den Scraper als Python-Modul
python -m rss_analyzer.scraper

pause
