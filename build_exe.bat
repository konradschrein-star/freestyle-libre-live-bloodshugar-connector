@echo off
title Build Standalone Windows EXE
echo ========================================================
echo   Building FreeStyle Libre Standalone Taskbar .EXE
echo ========================================================
echo.

python -m pip install pyinstaller

python generate_icon.py

python -m PyInstaller --noconfirm --onefile --windowed ^
    --icon="assets/app_icon.ico" ^
    --add-data "src/static;src/static" ^
    --name "FreeStyleLibreTaskbar" ^
    main.py

echo.
echo ========================================================
echo Build complete! 
echo Your standalone executable is: dist\FreeStyleLibreTaskbar.exe
echo ========================================================
pause
