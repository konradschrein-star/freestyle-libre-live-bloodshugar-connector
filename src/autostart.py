"""
FreeStyle Libre Live Blood Sugar Connector - Windows Autostart Manager
Configures autostart on Windows logon via HKCU Run registry key.
"""

from __future__ import annotations
import os
import sys
import winreg
from pathlib import Path
from typing import Optional


REG_KEY_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
APP_NAME = "FreeStyleLibreTaskbarConnector"


def get_default_launch_command() -> str:
    """Get executable or python launch command for this application."""
    # Check if frozen by PyInstaller
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}"'
    
    # Or python script
    base_dir = Path(__file__).resolve().parent.parent
    main_script = base_dir / "main.py"
    # Use pythonw.exe if available to avoid opening a black terminal window
    python_exe = sys.executable
    pythonw_exe = python_exe.replace("python.exe", "pythonw.exe")
    if os.path.exists(pythonw_exe):
        exe_to_use = pythonw_exe
    else:
        exe_to_use = python_exe

    return f'"{exe_to_use}" "{main_script}"'


def is_autostart_enabled() -> bool:
    """Check if autostart registry entry currently exists."""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY_PATH, 0, winreg.KEY_READ) as key:
            winreg.QueryValueEx(key, APP_NAME)
            return True
    except FileNotFoundError:
        return False
    except Exception as e:
        print(f"[Autostart] Error reading registry: {e}")
        return False


def set_autostart(enable: bool, command: Optional[str] = None) -> bool:
    """Enable or disable Windows autostart."""
    if command is None:
        command = get_default_launch_command()

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_KEY_PATH, 0, winreg.KEY_SET_VALUE) as key:
            if enable:
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, command)
                print(f"[Autostart] Enabled: {command}")
            else:
                try:
                    winreg.DeleteValue(key, APP_NAME)
                    print("[Autostart] Disabled.")
                except FileNotFoundError:
                    pass
        return True
    except Exception as e:
        print(f"[Autostart] Error updating registry: {e}")
        return False
