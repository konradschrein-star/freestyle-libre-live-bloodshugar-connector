"""
FreeStyle Libre Live Blood Sugar Connector - Configuration & Settings Module
Handles persistent local configuration for credentials, target ranges, units, and preferences.
Uses %APPDATA%/FreeStyleLibreTaskbar for PowerToys-like native Windows integration.
"""

from __future__ import annotations
import json
import os
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal, Optional


def get_app_data_dir() -> Path:
    """Get persistent application directory in %APPDATA% or local fallback."""
    if os.name == "nt":
        appdata = os.environ.get("APPDATA")
        if appdata:
            path = Path(appdata) / "FreeStyleLibreTaskbar"
            path.mkdir(parents=True, exist_ok=True)
            return path
    base_dir = Path(__file__).resolve().parent.parent
    return base_dir


def get_static_dir() -> Path:
    """Get static assets directory for dev and PyInstaller frozen runtime."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        # PyInstaller bundle directory
        bundle_static = Path(sys._MEIPASS) / "src" / "static"
        if bundle_static.exists():
            return bundle_static
        # Alternatively top-level static
        top_static = Path(sys._MEIPASS) / "static"
        if top_static.exists():
            return top_static

    return Path(__file__).resolve().parent / "static"


@dataclass
class GlucoseTargetRanges:
    """Glucose target thresholds stored in mg/dL (with mmol/L helpers)."""
    very_low: float = 54.0     # Critical low threshold (< 3.0 mmol/L / < 54 mg/dL)
    low: float = 70.0          # Low threshold (3.9 mmol/L / 70 mg/dL)
    target_low: float = 70.0   # Target lower bound (3.9 mmol/L / 70 mg/dL)
    target_high: float = 180.0 # Target upper bound (10.0 mmol/L / 180 mg/dL)
    high: float = 250.0        # High threshold (13.9 mmol/L / 250 mg/dL)

    # Conversion helper factor: 1 mmol/L = 18.0182 mg/dL
    @staticmethod
    def mgdl_to_mmol(val: float) -> float:
        return round(val / 18.0182, 1)

    @staticmethod
    def mmol_to_mgdl(val: float) -> float:
        return round(val * 18.0182, 1)

    @property
    def target_low_mmol(self) -> float:
        return self.mgdl_to_mmol(self.target_low)

    @property
    def target_high_mmol(self) -> float:
        return self.mgdl_to_mmol(self.target_high)

    @property
    def very_low_mmol(self) -> float:
        return self.mgdl_to_mmol(self.very_low)

    @property
    def high_mmol(self) -> float:
        return self.mgdl_to_mmol(self.high)


@dataclass
class AppConfig:
    """Application user configuration."""
    # LibreLinkUp Credentials
    email: str = ""
    password: str = ""
    region: str = "eu"  # "eu", "de", "eu2", "us", "ap", "ca"
    patient_id: Optional[str] = None
    patient_name: Optional[str] = None

    # Display Preferences - Default to mmol/L as requested
    unit: Literal["mmol/L", "mg/dL"] = "mmol/L"
    language: Literal["de", "en"] = "de"
    refresh_interval_seconds: int = 60  # Default 60 seconds
    
    # Target Ranges
    targets: GlucoseTargetRanges = field(default_factory=GlucoseTargetRanges)

    # Notifications & Audio
    enable_notifications: bool = True
    notify_on_low: bool = True
    notify_on_high: bool = True
    sound_alerts: bool = False

    # Web Dashboard
    web_host: str = "127.0.0.1"
    web_port: int = 8765

    # PowerToys-like Automatic Background Autostart (Enabled by default)
    autostart_with_windows: bool = True
    setup_completed: bool = False

    # Cached Auth Token (for fast resume without re-logging in every startup)
    cached_token: Optional[str] = None
    cached_token_expiry: Optional[int] = None
    cached_account_id: Optional[str] = None


class ConfigManager:
    """Thread-safe manager for loading and storing application configuration."""

    def __init__(self, config_path: Optional[Path] = None) -> None:
        if config_path is None:
            self.config_path = get_app_data_dir() / "config.json"
        else:
            self.config_path = config_path

        self.config: AppConfig = self.load()

    def load(self) -> AppConfig:
        """Load configuration from JSON file or return default configuration."""
        if not self.config_path.exists():
            default_cfg = AppConfig()
            self.save(default_cfg)
            return default_cfg

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            targets_data = data.get("targets", {})
            targets = GlucoseTargetRanges(
                very_low=float(targets_data.get("very_low", 54.0)),
                low=float(targets_data.get("low", 70.0)),
                target_low=float(targets_data.get("target_low", 70.0)),
                target_high=float(targets_data.get("target_high", 180.0)),
                high=float(targets_data.get("high", 250.0)),
            )

            cfg = AppConfig(
                email=data.get("email", ""),
                password=data.get("password", ""),
                region=data.get("region", "eu"),
                patient_id=data.get("patient_id"),
                patient_name=data.get("patient_name"),
                unit=data.get("unit", "mmol/L"),
                language=data.get("language", "de"),
                refresh_interval_seconds=int(data.get("refresh_interval_seconds", 60)),
                targets=targets,
                enable_notifications=bool(data.get("enable_notifications", True)),
                notify_on_low=bool(data.get("notify_on_low", True)),
                notify_on_high=bool(data.get("notify_on_high", True)),
                sound_alerts=bool(data.get("sound_alerts", False)),
                web_host=data.get("web_host", "127.0.0.1"),
                web_port=int(data.get("web_port", 8765)),
                autostart_with_windows=bool(data.get("autostart_with_windows", True)),
                setup_completed=bool(data.get("setup_completed", False)),
                cached_token=data.get("cached_token"),
                cached_token_expiry=data.get("cached_token_expiry"),
                cached_account_id=data.get("cached_account_id"),
            )
            return cfg
        except Exception as e:
            print(f"[ConfigManager] Error reading config from {self.config_path}: {e}. Using defaults.")
            return AppConfig()

    def save(self, cfg: Optional[AppConfig] = None) -> None:
        """Persist current configuration to JSON file."""
        if cfg is not None:
            self.config = cfg

        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            data = asdict(self.config)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"[ConfigManager] Error saving config to {self.config_path}: {e}")

    def is_configured(self) -> bool:
        """Check if user has completed setup and provided LibreLinkUp credentials."""
        return bool(self.config.email.strip() and self.config.password.strip())
