"""
FreeStyle Libre Live Blood Sugar Connector - Main Entry Point
Microsoft PowerToys-like native Windows utility with single-instance port locking,
automatic background startup, local web dashboard, and system tray monitor.
"""

from __future__ import annotations
import asyncio
import logging
import os
import socket
import sys
import threading
import time
import webbrowser
import uvicorn

# 1. Ensure sys.stdout and sys.stderr are valid (prevent crashes in PyInstaller --windowed mode)
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")

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


def is_port_available(host: str, port: int) -> bool:
    """Check if we can bind to the port (True = port is free, False = port is already in use)."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind((host, port))
        sock.close()
        return True
    except OSError:
        return False


def wait_for_port(host: str, port: int, timeout: float = 6.0) -> bool:
    """Wait until the server is actively listening and accepting connections on the port."""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.2)
                if s.connect_ex((host, port)) == 0:
                    return True
        except Exception:
            pass
        time.sleep(0.1)
    return False


def run_web_server(app, host: str, port: int) -> None:
    """Run uvicorn ASGI server in background thread with dedicated asyncio event loop."""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        config = uvicorn.Config(
            app=app,
            host=host,
            port=port,
            log_level="error",
            log_config=None,  # Do not attach stdout formatters in windowed mode
            access_log=False,
            loop="asyncio",
        )
        server = uvicorn.Server(config)
        loop.run_until_complete(server.serve())
    except Exception as e:
        logger.error(f"Fatal error in web server thread: {e}", exc_info=True)


def main() -> None:
    """Master application entrypoint."""
    config_mgr = ConfigManager()
    cfg = config_mgr.config

    # 1. Single-Instance Check (PowerToys behavior: focus existing instance if already running)
    if not is_port_available(cfg.web_host, cfg.web_port):
        logger.info(f"Port {cfg.web_port} already in use. Focusing existing instance in browser...")
        webbrowser.open(f"http://{cfg.web_host}:{cfg.web_port}")
        sys.exit(0)

    logger.info("Initializing FreeStyle Libre Live Taskbar Connector...")

    # 2. Initialize Storage & Database
    db_mgr = DatabaseManager()

    # 3. Ensure Windows Autostart is registered
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

    # 7. First-run onboarding: Wait until web server is active, then open browser
    if not config_mgr.is_configured() or not cfg.setup_completed:
        logger.info("First run detected: Waiting for web server and launching setup wizard...")
        def open_browser_when_ready():
            if wait_for_port(cfg.web_host, cfg.web_port, timeout=8.0):
                time.sleep(0.2)
                webbrowser.open(f"http://{cfg.web_host}:{cfg.web_port}")
            else:
                logger.error("Web server did not start within timeout.")

        threading.Thread(target=open_browser_when_ready, daemon=True).start()

    # 8. Start System Tray event loop (runs on main thread)
    try:
        tray_app.start()
    except KeyboardInterrupt:
        logger.info("Interrupted by user. Shutting down...")
    except Exception as e:
        logger.error(f"Error in tray app loop: {e}", exc_info=True)
    finally:
        tray_app.stop()
        logger.info("Application terminated cleanly.")


if __name__ == "__main__":
    main()
