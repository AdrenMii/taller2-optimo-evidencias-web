@echo off
cd /d "%~dp0"
python informe.py
if errorlevel 1 (
  echo.
  echo Error. Verifica que Python y scipy esten instalados:  pip install scipy numpy
  pause
)
