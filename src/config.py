"""
FreeStyle Libre Live Blood Sugar Connector - Configuration & Settings Module
Handles persistent local configuration for credentials, target ranges, units, and preferences.
"""

from __future__ import annotations
import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Literal, Optional


@dataclass
class GlucoseTargetRanges:
    """Glucose target thresholds in mg/dL."""
    very_low: float = 54.0   # Critical low threshold (<54 mg/dL -> Urgent Red)
    low: float = 70.0        # Low threshold (54-70 mg/dL -> Warning Yellow)
    target_low: float = 70.0 # Target lower bound (70-180 mg/dL -> Normal Green)
    target_high: float = 180.0 # Target upper bound
    high: float = 250.0      # High threshold (180-250 mg/dL -> Warning Yellow, >250 -> Urgent Red)


@dataclass
class AppConfig:
    """Application user configuration."""
    # LibreLinkUp Credentials
    email: str = ""
    password: str = ""
    region: str = "eu"  # "eu", "de", "eu2", "us", "ap", "auto"
    patient_id: Optional[str] = None
    patient_name: Optional[str] = None

    # Display Preferences
    unit: Literal["mg/dL", "mmol/L"] = "mg/dL"
    language: Literal["de", "en"] = "de"
    refresh_interval_seconds: int = 60  # Check every 60 seconds (Libre 3 streams every 1-5 mins)
    
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

    # System & Startup
    autostart_with_windows: bool = False

    # Cached Auth Token (for fast resume without re-logging in every startup)
    cached_token: Optional[str] = None
    cached_token_expiry: Optional[int] = None
    cached_account_id: Optional[str] = None


class ConfigManager:
    """Thread-safe manager for loading and storing application configuration."""

    def __init__(self, config_path: Optional[Path] = None) -> None:
        if config_path is None:
            # Default to config.json in the application root directory
            base_dir = Path(__file__).resolve().parent.parent
            self.config_path = base_dir / "config.json"
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
                unit=data.get("unit", "mg/dL"),
                language=data.get("language", "de"),
                refresh_interval_seconds=int(data.get("refresh_interval_seconds", 60)),
                targets=targets,
                enable_notifications=bool(data.get("enable_notifications", True)),
                notify_on_low=bool(data.get("notify_on_low", True)),
                notify_on_high=bool(data.get("notify_on_high", True)),
                sound_alerts=bool(data.get("sound_alerts", False)),
                web_host=data.get("web_host", "127.0.0.1"),
                web_port=int(data.get("web_port", 8765)),
                autostart_with_windows=bool(data.get("autostart_with_windows", False)),
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
        """Check if user has provided LibreLinkUp credentials."""
        return bool(self.config.email.strip() and self.config.password.strip())
