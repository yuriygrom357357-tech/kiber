@echo off
rem KIBR offline launcher for Windows
set "F=%~dp0kibr-data\index.html"
if not exist "%F%" (
  echo Folder kibr-data not found. Copy the whole KIBR folder.
  pause
  exit /b 1
)
for %%B in ("%ProgramFiles%\Google\Chrome\Application\chrome.exe" "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe" "%LocalAppData%\Google\Chrome\Application\chrome.exe" "%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe" "%ProgramFiles%\Microsoft\Edge\Application\msedge.exe") do (
  if exist %%B (
    start "" %%B --new-window "%F%"
    exit /b 0
  )
)
start "" "%F%"
