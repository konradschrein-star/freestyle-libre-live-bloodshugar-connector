"""
FreeStyle Libre Live Blood Sugar Connector - System Tray Integration
Renders dynamic, high-contrast taskbar icons, context menus, and Windows balloon notifications.
"""

from __future__ import annotations
import datetime
import logging
import threading
import time
import webbrowser
from typing import Optional
from PIL import Image
import pystray

from .config import ConfigManager
from .libre_client import GlucoseReading, LibreClient, SensorInfo
from .storage import DatabaseManager
from .tray_icon import (
    COLOR_GRAY,
    COLOR_GREEN,
    create_glucose_icon,
    create_offline_icon,
    get_status_color,
)
from .desktop_window import show_desktop_window

logger = logging.getLogger("TrayApp")


class TrayApplication:
    """Manages the Windows System Tray Icon, context menu, and background sync worker."""

    def __init__(self, config_mgr: ConfigManager, db_mgr: DatabaseManager) -> None:
        self.config_mgr = config_mgr
        self.db_mgr = db_mgr
        self.client: Optional[LibreClient] = None
        self.icon: Optional[pystray.Icon] = None
        self.is_running = False
        self.sync_thread: Optional[threading.Thread] = None
        self.latest_reading: Optional[GlucoseReading] = None
        self.active_sensor: Optional[SensorInfo] = None
        self._last_alert_ts: Optional[datetime.datetime] = None

        self._init_libre_client()

    def _init_libre_client(self) -> None:
        """Instantiate LibreLinkUp API client if credentials are configured."""
        cfg = self.config_mgr.config
        if self.config_mgr.is_configured():
            self.client = LibreClient(
                email=cfg.email,
                password=cfg.password,
                region=cfg.region,
                cached_token=cfg.cached_token,
                cached_account_id=cfg.cached_account_id,
            )
        else:
            self.client = None

    def start(self) -> None:
        """Start the tray icon and the background polling worker thread."""
        self.is_running = True

        # Initialize with cached reading or offline placeholder
        cached = self.db_mgr.get_latest_reading()
        if cached:
            self.latest_reading = cached
            initial_image = self._render_icon_image(cached)
            title_text = self._build_tooltip(cached)
        else:
            initial_image = create_offline_icon()
            title_text = "FreeStyle Libre 3 • Verbinde..."

        # Build context menu
        menu = pystray.Menu(
            pystray.MenuItem("📊 Dashboard & Diagramm", self._on_open_dashboard, default=True),
            pystray.MenuItem("🔄 Jetzt aktualisieren", self._on_manual_sync),
            pystray.MenuItem("⚙️ Einstellungen", self._on_open_settings),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("❌ Beenden", self._on_exit),
        )

        self.icon = pystray.Icon(
            name="FreeStyleLibreTaskbar",
            icon=initial_image,
            title=title_text,
            menu=menu,
        )

        # Start background polling thread
        self.sync_thread = threading.Thread(target=self._polling_loop, daemon=True)
        self.sync_thread.start()

        # Run system tray event loop on the main thread
        logger.info("Starting System Tray event loop...")
        self.icon.run()

    def stop(self) -> None:
        """Stop background worker and remove tray icon."""
        self.is_running = False
        if self.client:
            self.client.close()
        if self.icon:
            try:
                self.icon.stop()
            except Exception:
                pass

    def sync_data(self) -> Optional[GlucoseReading]:
        """Fetch latest reading from Abbott, update SQLite DB, and re-render tray icon."""
        if not self.config_mgr.is_configured():
            logger.info("Credentials not configured yet.")
            return None

        if not self.client:
            self._init_libre_client()

        if not self.client:
            return None

        try:
            reading, sensor = self.client.get_latest_reading()
            self.latest_reading = reading
            self.active_sensor = sensor

            # 1. Store reading into SQLite
            self.db_mgr.insert_reading(reading)

            # 2. Update cached auth token if renewed
            cfg = self.config_mgr.config
            if self.client.token and self.client.token != cfg.cached_token:
                cfg.cached_token = self.client.token
                cfg.cached_account_id = self.client.account_id
                self.config_mgr.save(cfg)

            # 3. Update Tray Icon image and tooltip
            if self.icon:
                try:
                    new_image = self._render_icon_image(reading)
                    self.icon.icon = new_image
                    self.icon.title = self._build_tooltip(reading)
                except Exception as icon_err:
                    logger.debug(f"Tray icon update deferred: {icon_err}")

            # 4. Check for threshold notifications
            self._check_alerts(reading)

            return reading

        except Exception as e:
            logger.error(f"Sync error: {e}")
            if self.icon and not self.latest_reading:
                try:
                    self.icon.icon = create_offline_icon()
                    self.icon.title = f"FreeStyle Libre: Verbindungsfehler ({str(e)[:40]})"
                except Exception:
                    pass
            return None

    def _render_icon_image(self, reading: GlucoseReading) -> Image.Image:
        """Render high-contrast, ultra-bold icon image for taskbar display."""
        cfg = self.config_mgr.config
        is_mmol = (cfg.unit == "mmol/L")
        val_str = f"{reading.value_mmol:.1f}" if is_mmol else f"{reading.value_mgdl:.0f}"

        bg_color = get_status_color(
            value_mgdl=reading.value_mgdl,
            very_low=cfg.targets.very_low,
            low=cfg.targets.target_low,
            target_high=cfg.targets.target_high,
            high=cfg.targets.high,
        )

        return create_glucose_icon(
            value_str=val_str,
            trend_symbol=reading.trend_symbol,
            bg_color=bg_color,
            size=64,
        )

    def _build_tooltip(self, reading: GlucoseReading) -> str:
        """Create informative Windows taskbar tooltip."""
        cfg = self.config_mgr.config
        val_display = f"{reading.value_mmol:.1f} mmol/L" if cfg.unit == "mmol/L" else f"{reading.value_mgdl:.0f} mg/dL"
        time_str = reading.timestamp.strftime("%H:%M")
        status_txt = reading.status_label_de if cfg.language == "de" else reading.status_label_en

        return (
            f"Blutzucker: {val_display} {reading.trend_symbol} ({status_txt})\n"
            f"Sensor: {reading.sensor_serial or 'Libre 3'}\n"
            f"Stand: {time_str} Uhr"
        )

    def _check_alerts(self, reading: GlucoseReading) -> None:
        """Send Windows notification if reading exceeds clinical thresholds."""
        cfg = self.config_mgr.config
        if not cfg.enable_notifications or not self.icon:
            return

        now = datetime.datetime.now()
        if self._last_alert_ts and (now - self._last_alert_ts).total_seconds() < 900:
            return  # Snooze for 15 minutes

        val_display = f"{reading.value_mmol:.1f} mmol/L" if cfg.unit == "mmol/L" else f"{reading.value_mgdl:.0f} mg/dL"

        if reading.is_low and cfg.notify_on_low:
            self.icon.notify(
                title="⚠️ Niedriger Blutzucker!",
                message=f"Aktueller Wert: {val_display} {reading.trend_symbol} ({reading.trend_description_de})",
            )
            self._last_alert_ts = now
        elif reading.is_high and cfg.notify_on_high:
            self.icon.notify(
                title="⚠️ Erhöhter Blutzucker!",
                message=f"Aktueller Wert: {val_display} {reading.trend_symbol} ({reading.trend_description_de})",
            )
            self._last_alert_ts = now

    def _polling_loop(self) -> None:
        """Background loop executing periodic synchronization."""
        # Initial sync on startup (wait 1.5s for tray window initialization)
        time.sleep(1.5)
        self.sync_data()

        while self.is_running:
            interval = max(15, self.config_mgr.config.refresh_interval_seconds)
            for _ in range(interval):
                if not self.is_running:
                    return
                time.sleep(1.0)

            if self.is_running:
                self.sync_data()

    def _on_open_dashboard(self, icon, item) -> None:
        """Open native desktop app window (or fallback to browser)."""
        cfg = self.config_mgr.config
        url = f"http://{cfg.web_host}:{cfg.web_port}"
        try:
            show_desktop_window(url)
        except Exception:
            webbrowser.open(url)

    def _on_open_settings(self, icon, item) -> None:
        """Open settings dialog."""
        cfg = self.config_mgr.config
        url = f"http://{cfg.web_host}:{cfg.web_port}"
        try:
            show_desktop_window(url)
        except Exception:
            webbrowser.open(url)

    def _on_manual_sync(self, icon, item) -> None:
        """Handle manual 'Jetzt aktualisieren' menu click."""
        threading.Thread(target=self.sync_data, daemon=True).start()

    def _on_exit(self, icon, item) -> None:
        """Exit the application completely."""
        logger.info("User requested exit from tray context menu.")
        self.stop()
