"""
FreeStyle Libre Live Blood Sugar Connector - Standalone Desktop App Window
Launches the dashboard in native standalone App Mode (Edge/Chrome App Window) with zero browser chrome, no address bar, and dedicated window frame.
"""

from __future__ import annotations
import logging
import os
import subprocess
import webbrowser
from typing import Optional

logger = logging.getLogger("DesktopWindow")


def show_desktop_window(
    url: str = "http://127.0.0.1:8765",
    width: int = 1200,
    height: int = 840,
) -> None:
    """
    Open the dashboard as a true standalone desktop application window.
    Uses Microsoft Edge / Chrome App Mode for a dedicated, borderless desktop window.
    """
    browser_candidates = [
        os.path.expandvars(r"%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%LocalAppData%\Microsoft\Edge\Application\msedge.exe"),
        os.path.expandvars(r"%ProgramFiles%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"),
        os.path.expandvars(r"%LocalAppData%\Google\Chrome\Application\chrome.exe"),
    ]

    for exe_path in browser_candidates:
        if os.path.exists(exe_path):
            try:
                cmd = [
                    exe_path,
                    f"--app={url}",
                    f"--window-size={width},{height}",
                    "--disable-extensions",
                    "--disable-plugins",
                ]
                subprocess.Popen(cmd)
                logger.info(f"Opened standalone desktop app window via {exe_path}")
                return
            except Exception as e:
                logger.error(f"Failed to launch app window via {exe_path}: {e}")

    # Fallback to default system browser
    logger.info("Falling back to system default browser")
    webbrowser.open(url)
