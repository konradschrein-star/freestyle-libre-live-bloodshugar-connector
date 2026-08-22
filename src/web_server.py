"""
FreeStyle Libre Live Blood Sugar Connector - Local Web Server & REST API
Provides local web dashboard, real-time analytics, and in-app connection configuration.
"""

from __future__ import annotations
import datetime
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import uvicorn
from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .config import AppConfig, ConfigManager, GlucoseTargetRanges
from .libre_client import LibreClient, GlucoseReading
from .storage import DatabaseManager
from .autostart import is_autostart_enabled, set_autostart


class ConfigUpdateRequest(BaseModel):
    email: str
    password: Optional[str] = None
    region: str = "eu"
    unit: str = "mmol/L"
    language: str = "de"
    refresh_interval_seconds: int = 60
    target_low: float = 70.0      # mg/dL
    target_high: float = 180.0    # mg/dL
    very_low: float = 54.0        # mg/dL
    high: float = 250.0           # mg/dL
    enable_notifications: bool = True
    notify_on_low: bool = True
    notify_on_high: bool = True
    sound_alerts: bool = False
    autostart_with_windows: bool = False
    setup_completed: bool = True


class TestConnectionRequest(BaseModel):
    email: str
    password: str
    region: str = "eu"


def create_app(
    config_mgr: ConfigManager,
    db_mgr: DatabaseManager,
    sync_callback: Optional[callable] = None,
) -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(title="FreeStyle Libre Connector", docs_url=None, redoc_url=None)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    static_dir = Path(__file__).resolve().parent / "static"
    static_dir.mkdir(parents=True, exist_ok=True)

    @app.get("/api/current")
    async def get_current() -> Dict[str, Any]:
        """Fetch current blood sugar reading and connection status."""
        latest = db_mgr.get_latest_reading()
        is_conf = config_mgr.is_configured()
        cfg = config_mgr.config

        if not latest:
            return {
                "status": "configured" if is_conf else "unconfigured",
                "reading": None,
                "configured": is_conf,
                "setup_completed": cfg.setup_completed,
                "email": cfg.email if is_conf else "",
                "unit": cfg.unit,
            }

        reading_dict = {
            "value_mgdl": latest.value_mgdl,
            "value_mmol": latest.value_mmol,
            "trend_arrow_id": latest.trend_arrow_id,
            "trend_symbol": latest.trend_symbol,
            "trend_description_de": latest.trend_description_de,
            "trend_description_en": latest.trend_description_en,
            "timestamp": latest.timestamp.isoformat(),
            "time_str": latest.timestamp.strftime("%H:%M:%S"),
            "measurement_color": latest.measurement_color,
            "status_label_de": latest.status_label_de,
            "status_label_en": latest.status_label_en,
            "is_high": latest.is_high,
            "is_low": latest.is_low,
            "patient_name": latest.patient_name,
            "sensor_serial": latest.sensor_serial,
            "unit": cfg.unit,
        }

        return {
            "status": "active",
            "reading": reading_dict,
            "configured": is_conf,
            "setup_completed": cfg.setup_completed,
            "email": cfg.email,
            "unit": cfg.unit,
        }

    @app.get("/api/history")
    async def get_history(hours: int = 24) -> Dict[str, Any]:
        """Fetch glucose readings history for charting."""
        cutoff = datetime.datetime.now() - datetime.timedelta(hours=hours)
        readings = db_mgr.get_readings_since(cutoff)
        
        cfg = config_mgr.config
        points = [
            {
                "timestamp": r.timestamp.isoformat(),
                "time_label": r.timestamp.strftime("%H:%M"),
                "value_mgdl": r.value_mgdl,
                "value_mmol": r.value_mmol,
                "trend_symbol": r.trend_symbol,
                "color_code": r.measurement_color,
            }
            for r in readings
        ]
        return {
            "hours": hours,
            "unit": cfg.unit,
            "targets": {
                "target_low_mgdl": cfg.targets.target_low,
                "target_high_mgdl": cfg.targets.target_high,
                "very_low_mgdl": cfg.targets.very_low,
                "high_mgdl": cfg.targets.high,
                "target_low_mmol": cfg.targets.target_low_mmol,
                "target_high_mmol": cfg.targets.target_high_mmol,
                "very_low_mmol": cfg.targets.very_low_mmol,
                "high_mmol": cfg.targets.high_mmol,
            },
            "points": points,
        }

    @app.get("/api/stats")
    async def get_stats(hours: int = 24) -> Dict[str, Any]:
        """Get clinical glycemic metrics and Time in Range."""
        stats = db_mgr.get_statistics(hours=hours, targets=config_mgr.config.targets)
        stats["unit"] = config_mgr.config.unit
        return stats

    @app.get("/api/config")
    async def get_config() -> Dict[str, Any]:
        """Get application configuration."""
        cfg = config_mgr.config
        return {
            "email": cfg.email,
            "has_password": bool(cfg.password),
            "region": cfg.region,
            "unit": cfg.unit,
            "language": cfg.language,
            "refresh_interval_seconds": cfg.refresh_interval_seconds,
            "targets": {
                "very_low": cfg.targets.very_low,
                "low": cfg.targets.low,
                "target_low": cfg.targets.target_low,
                "target_high": cfg.targets.target_high,
                "high": cfg.targets.high,
                "very_low_mmol": cfg.targets.very_low_mmol,
                "low_mmol": cfg.targets.target_low_mmol,
                "target_low_mmol": cfg.targets.target_low_mmol,
                "target_high_mmol": cfg.targets.target_high_mmol,
                "high_mmol": cfg.targets.high_mmol,
            },
            "enable_notifications": cfg.enable_notifications,
            "notify_on_low": cfg.notify_on_low,
            "notify_on_high": cfg.notify_on_high,
            "sound_alerts": cfg.sound_alerts,
            "setup_completed": cfg.setup_completed,
            "autostart_with_windows": is_autostart_enabled(),
        }

    @app.post("/api/config")
    async def update_config(req: ConfigUpdateRequest) -> Dict[str, Any]:
        """Update settings and trigger re-authentication if credentials changed."""
        cfg = config_mgr.config
        cfg.email = req.email.strip()
        if req.password:  # Only update password if provided
            cfg.password = req.password.strip()
            cfg.cached_token = None  # Clear cache to force fresh login

        cfg.region = req.region.lower()
        cfg.unit = "mg/dL" if req.unit == "mg/dL" else "mmol/L"
        cfg.language = "en" if req.language == "en" else "de"
        cfg.refresh_interval_seconds = max(15, req.refresh_interval_seconds)

        cfg.targets.very_low = req.very_low
        cfg.targets.low = req.target_low
        cfg.targets.target_low = req.target_low
        cfg.targets.target_high = req.target_high
        cfg.targets.high = req.high

        cfg.enable_notifications = req.enable_notifications
        cfg.notify_on_low = req.notify_on_low
        cfg.notify_on_high = req.notify_on_high
        cfg.sound_alerts = req.sound_alerts
        cfg.autostart_with_windows = req.autostart_with_windows
        cfg.setup_completed = req.setup_completed

        # Update Windows Registry for Autostart
        set_autostart(req.autostart_with_windows)

        config_mgr.save(cfg)

        # Trigger sync immediately in background
        if sync_callback:
            try:
                sync_callback()
            except Exception as e:
                print(f"[API] Error in sync_callback: {e}")

        return {"status": "success", "message": "Einstellungen erfolgreich gespeichert."}

    @app.post("/api/test-connection")
    async def test_connection(req: TestConnectionRequest) -> Dict[str, Any]:
        """Test LibreLinkUp credentials and retrieve sensor info immediately."""
        client = LibreClient(
            email=req.email,
            password=req.password,
            region=req.region,
        )
        try:
            auth_res = client.authenticate()
            if not auth_res.success:
                return {
                    "success": False,
                    "message": auth_res.error_message or "Anmeldung fehlgeschlagen.",
                }

            reading, sensor = client.get_latest_reading()
            cfg = config_mgr.config
            val_display = f"{reading.value_mmol:.1f} mmol/L" if cfg.unit == "mmol/L" else f"{reading.value_mgdl:.0f} mg/dL"
            
            return {
                "success": True,
                "message": "Verbindung zu FreeStyle LibreLinkUp erfolgreich hergestellt!",
                "patient_name": reading.patient_name,
                "sensor_serial": reading.sensor_serial or "FreeStyle Libre 3",
                "current_mgdl": reading.value_mgdl,
                "current_mmol": reading.value_mmol,
                "current_display": val_display,
                "trend_symbol": reading.trend_symbol,
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Fehler bei Verbindungsaufbau: {str(e)}",
            }
        finally:
            client.close()

    @app.post("/api/refresh-now")
    async def refresh_now() -> Dict[str, Any]:
        """Trigger immediate data fetch from Abbott."""
        if sync_callback:
            try:
                reading = sync_callback()
                return {"status": "success", "message": "Daten aktualisiert."}
            except Exception as e:
                return {"status": "error", "message": str(e)}
        return {"status": "error", "message": "No sync callback configured"}

    @app.get("/api/export/csv")
    async def export_csv() -> Response:
        """Download all readings as CSV file."""
        export_file = Path(__file__).resolve().parent.parent / "glucose_export.csv"
        db_mgr.export_to_csv(export_file)
        return FileResponse(
            path=str(export_file),
            filename=f"freestyle_libre_export_{datetime.date.today().isoformat()}.csv",
            media_type="text/csv",
        )

    @app.get("/", response_class=HTMLResponse)
    async def index() -> HTMLResponse:
        """Serve main dashboard and setup interface."""
        index_path = static_dir / "index.html"
        if index_path.exists():
            return HTMLResponse(content=index_path.read_text(encoding="utf-8"))
        return HTMLResponse(content="<h1>Dashboard wird initialisiert...</h1>")

    # Mount static assets if any
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    return app
