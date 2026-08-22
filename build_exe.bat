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
    --hidden-import="uvicorn.lifespan.off" ^
    --hidden-import="uvicorn.lifespan.on" ^
    --hidden-import="uvicorn.protocols.http.auto" ^
    --hidden-import="uvicorn.protocols.http.h11_impl" ^
    --hidden-import="uvicorn.protocols.websockets.auto" ^
    --hidden-import="anyio._backends._asyncio" ^
    --name "FreeStyleLibreTaskbar" ^
    main.py

echo.
echo ========================================================
echo Build complete! 
echo Your standalone executable is: dist\FreeStyleLibreTaskbar.exe
echo ========================================================
pause
