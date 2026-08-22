"""
FreeStyle Libre Live Blood Sugar Connector - Main Entry Point
Orchestrates the local web server, database storage, and Windows taskbar tray monitor.
"""

from __future__ import annotations
import logging
import os
import sys
import threading
import time
import webbrowser
import uvicorn

from src.config import ConfigManager
from src.storage import DatabaseManager
from src.web_server import create_app
from src.tray_app import TrayApplication

# Configure root logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("Main")


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
    """Application main entrypoint."""
    logger.info("Initializing FreeStyle Libre Live Blood Sugar Connector...")

    # 1. Initialize Configuration & Database
    config_mgr = ConfigManager()
    db_mgr = DatabaseManager()

    # 2. Instantiate System Tray Application
    tray_app = TrayApplication(config_mgr=config_mgr, db_mgr=db_mgr)

    # 3. Create FastAPI app with sync callback
    api_app = create_app(
        config_mgr=config_mgr,
        db_mgr=db_mgr,
        sync_callback=lambda: tray_app.sync_data(),
    )

    # 4. Start Web Server in background daemon thread
    cfg = config_mgr.config
    web_thread = threading.Thread(
        target=run_web_server,
        args=(api_app, cfg.web_host, cfg.web_port),
        daemon=True,
    )
    web_thread.start()
    logger.info(f"Local Web Dashboard running at http://{cfg.web_host}:{cfg.web_port}")

    # 5. If not configured on startup, automatically open the setup page
    if not config_mgr.is_configured():
        logger.info("First run detected: Opening configuration dashboard in browser...")
        def open_browser_delayed():
            time.sleep(1.2)
            webbrowser.open(f"http://{cfg.web_host}:{cfg.web_port}")
        threading.Thread(target=open_browser_delayed, daemon=True).start()

    # 6. Start System Tray event loop (main thread)
    try:
        tray_app.start()
    except KeyboardInterrupt:
        logger.info("Interrupted by user. Shutting down...")
    finally:
        tray_app.stop()
        logger.info("Application terminated cleanly.")


if __name__ == "__main__":
    main()
