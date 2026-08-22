"""
FreeStyle Libre Live Blood Sugar Connector - Windows System Tray Application
Integrates dynamic taskbar tray icon next to Windows clock with rich context menu and alerts.
"""

from __future__ import annotations
import datetime
import logging
import threading
import time
import webbrowser
from typing import Optional
import pystray
from PIL import Image

from .config import AppConfig, ConfigManager
from .storage import DatabaseManager
from .libre_client import LibreClient, GlucoseReading
from .tray_icon import (
    create_glucose_icon,
    create_offline_icon,
    get_status_color,
    COLOR_GREEN,
    COLOR_YELLOW,
    COLOR_ORANGE,
    COLOR_RED,
    COLOR_GRAY,
)
from .autostart import is_autostart_enabled, set_autostart

logger = logging.getLogger("TrayApp")


class TrayApplication:
    """Manages the Windows Taskbar System Tray Icon and background synchronization loop."""

    def __init__(self, config_mgr: ConfigManager, db_mgr: DatabaseManager) -> None:
        self.config_mgr = config_mgr
        self.db_mgr = db_mgr
        self.icon: Optional[pystray.Icon] = None
        self.is_running = False
        self.sync_thread: Optional[threading.Thread] = None
        self.latest_reading: Optional[GlucoseReading] = None
        self.last_sync_time: Optional[datetime.datetime] = None
        self.client: Optional[LibreClient] = None
        self._lock = threading.Lock()

    def _init_client(self) -> Optional[LibreClient]:
        """Initialize or re-initialize LibreLinkUp client."""
        cfg = self.config_mgr.config
        if not cfg.email or not cfg.password:
            return None

        return LibreClient(
            email=cfg.email,
            password=cfg.password,
            region=cfg.region,
            cached_token=cfg.cached_token,
            cached_account_id=cfg.cached_account_id,
        )

    def sync_data(self) -> Optional[GlucoseReading]:
        """Fetch latest glucose reading from Abbott LibreLinkUp and update tray icon."""
        cfg = self.config_mgr.config
        if not self.config_mgr.is_configured():
            logger.info("Credentials not configured yet.")
            self._update_icon_offline("Bitte Konto verbinden")
            return None

        try:
            with self._lock:
                if self.client is None:
                    self.client = self._init_client()

                if self.client is None:
                    return None

                reading, sensor = self.client.get_latest_reading()

                # Cache token if changed
                if self.client.token and self.client.token != cfg.cached_token:
                    cfg.cached_token = self.client.token
                    cfg.cached_account_id = self.client.account_id
                    self.config_mgr.save(cfg)

                # Persist to local SQLite
                self.db_mgr.insert_reading(reading)

                # Update state
                self.latest_reading = reading
                self.last_sync_time = datetime.datetime.now()

                # Update Tray Icon
                self._update_icon_with_reading(reading)

                # Check for critical notifications
                if cfg.enable_notifications and self.icon:
                    if reading.value_mgdl < cfg.targets.very_low and cfg.notify_on_low:
                        self.icon.notify(
                            f"Kritisch niedriger Blutzucker: {reading.value_mgdl:.0f} mg/dL {reading.trend_symbol}",
                            "⚠️ Blutzucker-Warnung (Hypo)",
                        )
                    elif reading.value_mgdl > cfg.targets.high and cfg.notify_on_high:
                        self.icon.notify(
                            f"Hoher Blutzucker: {reading.value_mgdl:.0f} mg/dL {reading.trend_symbol}",
                            "⚠️ Blutzucker-Warnung (Hyper)",
                        )

                return reading

        except Exception as e:
            logger.error(f"Sync error: {e}")
            self._update_icon_offline(f"Verbindungsfehler: {e}")
            return None

    def _update_icon_with_reading(self, reading: GlucoseReading) -> None:
        """Render new dynamic tray bitmap from reading."""
        if not self.icon:
            return

        cfg = self.config_mgr.config
        is_mmol = cfg.unit == "mmol/L"

        if is_mmol:
            val_str = f"{reading.value_mmol:.1f}"
        else:
            val_str = f"{reading.value_mgdl:.0f}"

        bg_color = get_status_color(
            reading.value_mgdl,
            very_low=cfg.targets.very_low,
            low=cfg.targets.target_low,
            target_high=cfg.targets.target_high,
            high=cfg.targets.high,
        )

        icon_img = create_glucose_icon(
            value_str=val_str,
            trend_symbol=reading.trend_symbol,
            bg_color=bg_color,
        )

        self.icon.icon = icon_img
        
        # Tooltip
        status_text = reading.status_label_de if cfg.language == "de" else reading.status_label_en
        tooltip_str = (
            f"Blutzucker: {val_str} {cfg.unit} {reading.trend_symbol} ({status_text})\n"
            f"Sensor: {reading.sensor_serial or 'FreeStyle Libre 3'}"
        )
        self.icon.title = tooltip_str

    def _update_icon_offline(self, message: str = "Offline") -> None:
        """Render offline placeholder icon."""
        if not self.icon:
            return
        self.icon.icon = create_offline_icon()
        self.icon.title = f"FreeStyle Libre Connector - {message}"

    def _background_sync_loop(self) -> None:
        """Continuous background sync loop."""
        # Initial sync on startup
        time.sleep(1)
        self.sync_data()

        while self.is_running:
            cfg = self.config_mgr.config
            interval = max(15, cfg.refresh_interval_seconds)
            
            # Sleep in 1-second chunks for responsive shutdown
            for _ in range(interval):
                if not self.is_running:
                    break
                time.sleep(1)

            if self.is_running:
                self.sync_data()

    def _create_menu(self) -> pystray.Menu:
        """Generate the right-click context menu for the system tray icon."""
        cfg = self.config_mgr.config
        is_de = cfg.language == "de"

        def get_header_text(item) -> str:
            if self.latest_reading:
                r = self.latest_reading
                is_mmol = cfg.unit == "mmol/L"
                val = f"{r.value_mmol:.1f}" if is_mmol else f"{r.value_mgdl:.0f}"
                lbl = r.status_label_de if is_de else r.status_label_en
                return f"🟢 {val} {cfg.unit} {r.trend_symbol} ({lbl})"
            return "⏳ Verbinde mit FreeStyle Libre..." if is_de else "⏳ Connecting to Libre..."

        def get_stats_text(item) -> str:
            stats = self.db_mgr.get_statistics(hours=24, targets=cfg.targets)
            if stats["count"] > 0:
                is_mmol = cfg.unit == "mmol/L"
                avg = stats["average_mmol"] if is_mmol else stats["average_mgdl"]
                tir = stats["time_in_range"]["target_percent"]
                return f"📊 Ø 24h: {avg} {cfg.unit} | TIR: {tir}%"
            return "📊 24h Statistik: Keine Daten" if is_de else "📊 24h Stats: No data"

        def on_open_dashboard(icon, item):
            url = f"http://{cfg.web_host}:{cfg.web_port}"
            webbrowser.open(url)

        def on_open_settings(icon, item):
            url = f"http://{cfg.web_host}:{cfg.web_port}"
            webbrowser.open(url)

        def on_force_refresh(icon, item):
            threading.Thread(target=self.sync_data, daemon=True).start()

        def on_toggle_autostart(icon, item):
            curr = is_autostart_enabled()
            new_state = not curr
            set_autostart(new_state)
            cfg.autostart_with_windows = new_state
            self.config_mgr.save(cfg)

        def on_quit(icon, item):
            self.stop()

        items = [
            pystray.MenuItem(get_header_text, None, enabled=False),
            pystray.MenuItem(get_stats_text, None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "🔄 Jetzt aktualisieren" if is_de else "🔄 Refresh Now",
                on_force_refresh,
            ),
            pystray.MenuItem(
                "📊 Dashboard & Diagramm öffnen" if is_de else "📊 Open Dashboard",
                on_open_dashboard,
                default=True,  # Double-click tray icon opens dashboard
            ),
            pystray.MenuItem(
                "⚙️ Konto & Einstellungen" if is_de else "⚙️ Settings & Account",
                on_open_settings,
            ),
            pystray.MenuItem(
                "🪟 Mit Windows automatisch starten" if is_de else "🪟 Start with Windows",
                on_toggle_autostart,
                checked=lambda item: is_autostart_enabled(),
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "🚪 Beenden" if is_de else "🚪 Exit",
                on_quit,
            ),
        ]

        return pystray.Menu(*items)

    def start(self) -> None:
        """Start the system tray application and background sync worker."""
        self.is_running = True
        
        # Start background sync thread
        self.sync_thread = threading.Thread(target=self._background_sync_loop, daemon=True)
        self.sync_thread.start()

        # Create initial icon
        init_icon = create_offline_icon()
        self.icon = pystray.Icon(
            name="FreeStyleLibreTaskbar",
            icon=init_icon,
            title="FreeStyle Libre Connector (Wird gestartet...)",
            menu=self._create_menu(),
        )

        # Run tray event loop (blocks main thread until icon.stop())
        self.icon.run()

    def stop(self) -> None:
        """Stop background worker and remove tray icon."""
        self.is_running = False
        if self.client:
            self.client.close()
        if self.icon:
            self.icon.stop()
