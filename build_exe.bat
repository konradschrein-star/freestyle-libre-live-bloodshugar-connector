@echo off
title Build Standalone Windows EXE
echo ========================================================
echo   Building Standalone EXE with PyInstaller
echo ========================================================
echo.

pip install pyinstaller

pyinstaller --noconfirm --onedir --windowed ^
    --add-data "src/static;src/static" ^
    --name "FreeStyleLibreTaskbar" ^
    main.py

echo.
echo ========================================================
echo Build complete! Executable is located in dist/FreeStyleLibreTaskbar/
echo ========================================================
pause
