"""
FreeStyle Libre Live Blood Sugar Connector - Main Entry Point
Microsoft PowerToys-like native Windows utility with single-instance mutex,
automatic background startup, local web dashboard, and system tray monitor.
"""

from __future__ import annotations
import logging
import os
import sys
import threading
import time
import webbrowser
import winerror
import win32api
import win32event
import uvicorn

from src.config import ConfigManager, get_app_data_dir
from src.storage import DatabaseManager
from src.web_server import create_app
from src.tray_app import TrayApplication
from src.autostart import set_autostart, is_autostart_enabled

# Configure logging to write to %APPDATA%/FreeStyleLibreTaskbar/app.log and console
log_dir = get_app_data_dir()
log_file = log_dir / "app.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(str(log_file), encoding="utf-8"),
    ],
)
logger = logging.getLogger("Main")

MUTEX_NAME = "Global\\FreeStyleLibreTaskbar_SingleInstance_Mutex_v1"


def run_web_server(app, host: str, port: int) -> None:
    """Run uvicorn ASGI server in background thread."""
    config = uvicorn.Config(
        app=app,
        host=host,
        port=port,
        log_level="warning",
        access_log=False,
    )
    server = uvicorn.Server(config)
    server.run()


def main() -> None:
    """Master application entrypoint."""
    # 1. Single-Instance Check (PowerToys behavior)
    mutex = win32event.CreateMutex(None, False, MUTEX_NAME)
    if win32api.GetLastError() == winerror.ERROR_ALREADY_EXISTS:
        # App is already running in background! Open dashboard in browser and exit.
        logger.info("Application already running in background. Focusing dashboard...")
        webbrowser.open("http://127.0.0.1:8765")
        sys.exit(0)

    logger.info("Initializing FreeStyle Libre Live Taskbar Connector...")

    # 2. Initialize Configuration & Database
    config_mgr = ConfigManager()
    db_mgr = DatabaseManager()
    cfg = config_mgr.config

    # 3. Ensure Windows Autostart is registered (PowerToys-like seamless startup)
    if cfg.autostart_with_windows and not is_autostart_enabled():
        set_autostart(True)

    # 4. Instantiate System Tray Application
    tray_app = TrayApplication(config_mgr=config_mgr, db_mgr=db_mgr)

    # 5. Create FastAPI app with sync callback
    api_app = create_app(
        config_mgr=config_mgr,
        db_mgr=db_mgr,
        sync_callback=lambda: tray_app.sync_data(),
    )

    # 6. Start Web Server in background daemon thread
    web_thread = threading.Thread(
        target=run_web_server,
        args=(api_app, cfg.web_host, cfg.web_port),
        daemon=True,
    )
    web_thread.start()
    logger.info(f"Local Web Server running at http://{cfg.web_host}:{cfg.web_port}")

    # 7. First-run onboarding: If not configured, open the 4-step wizard
    if not config_mgr.is_configured() or not cfg.setup_completed:
        logger.info("First run detected: Launching setup wizard in browser...")
        def open_browser_delayed():
            time.sleep(1.2)
            webbrowser.open(f"http://{cfg.web_host}:{cfg.web_port}")
        threading.Thread(target=open_browser_delayed, daemon=True).start()

    # 8. Start System Tray event loop (runs on main thread)
    try:
        tray_app.start()
    except KeyboardInterrupt:
        logger.info("Interrupted by user. Shutting down...")
    finally:
        tray_app.stop()
        logger.info("Application terminated cleanly.")


if __name__ == "__main__":
    main()
