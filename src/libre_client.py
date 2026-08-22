"""
FreeStyle Libre / LibreLinkUp API Client
Robust, typed client for Abbott LibreLinkUp REST API supporting FreeStyle Libre 3 and Libre 2.
Features automatic region redirection, minimumVersion header auto-negotiation, and token caching.
"""

from __future__ import annotations
import datetime
import hashlib
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
import httpx

logger = logging.getLogger("LibreClient")


# Regional base URLs for Abbott LibreView / LibreLinkUp
REGIONAL_ENDPOINTS: Dict[str, str] = {
    "eu": "https://api-eu.libreview.io",
    "de": "https://api-de.libreview.io",
    "eu2": "https://api-eu2.libreview.io",
    "us": "https://api-us.libreview.io",
    "ap": "https://api-ap.libreview.io",
    "ca": "https://api-ca.libreview.io",
    "ae": "https://api-ae.libreview.io",
    "fr": "https://api-fr.libreview.io",
    "jp": "https://api-jp.libreview.io",
    "la": "https://api-la.libreview.io",
}

# Trend arrow mapping: ID -> (Symbol, English Description, German Description)
TREND_ARROWS: Dict[int, Tuple[str, str, str]] = {
    1: ("↓↓", "Falling quickly", "Stark fallend"),
    2: ("↓", "Falling", "Fallend"),
    3: ("→", "Stable", "Stabil"),
    4: ("↑", "Rising", "Steigend"),
    5: ("↑↑", "Rising quickly", "Stark steigend"),
    0: ("—", "Not determined", "Nicht ermittelt"),
}


@dataclass
class GlucoseReading:
    """Represents a single blood sugar reading with trend and metadata."""
    value_mgdl: float
    value_mmol: float
    trend_arrow_id: int
    trend_symbol: str
    trend_description_de: str
    trend_description_en: str
    timestamp: datetime.datetime
    is_high: bool
    is_low: bool
    measurement_color: int  # 1 = Green (Normal), 2 = Yellow (High), 3 = Orange (Low), 4 = Red (Critical)
    patient_id: str
    patient_name: str
    sensor_serial: Optional[str] = None
    raw_data: Dict[str, Any] = field(default_factory=dict)

    @property
    def status_label_de(self) -> str:
        if self.measurement_color == 1:
            return "Normal"
        elif self.measurement_color == 2:
            return "Erhöht"
        elif self.measurement_color == 3:
            return "Niedrig"
        elif self.measurement_color == 4:
            return "Kritisch"
        return "Normal"

    @property
    def status_label_en(self) -> str:
        if self.measurement_color == 1:
            return "In Range"
        elif self.measurement_color == 2:
            return "High"
        elif self.measurement_color == 3:
            return "Low"
        elif self.measurement_color == 4:
            return "Critical"
        return "In Range"


@dataclass
class SensorInfo:
    """Information about the currently active FreeStyle Libre sensor."""
    serial_number: str
    device_name: str
    activation_date: Optional[datetime.datetime]
    expiration_date: Optional[datetime.datetime]
    days_remaining: Optional[int]
    is_active: bool


@dataclass
class LibreAuthResult:
    """Result of authentication attempt."""
    success: bool
    token: Optional[str] = None
    account_id: Optional[str] = None
    expires_at: Optional[int] = None
    error_message: Optional[str] = None
    redirect_region: Optional[str] = None


class LibreClient:
    """
    Abbott LibreLinkUp REST API Client.
    Connects to the cloud follower API to stream real-time glucose readings.
    """

    DEFAULT_VERSION = "4.16.0"

    def __init__(
        self,
        email: str,
        password: str,
        region: str = "de",
        cached_token: Optional[str] = None,
        cached_account_id: Optional[str] = None,
    ) -> None:
        self.email = email.strip()
        self.password = password.strip()
        self.region = region.lower() if region else "de"
        self.base_url = REGIONAL_ENDPOINTS.get(self.region, REGIONAL_ENDPOINTS["de"])
        self.api_version = self.DEFAULT_VERSION
        self.token: Optional[str] = cached_token
        self.account_id: Optional[str] = cached_account_id
        self.patient_id: Optional[str] = None
        self.patient_name: Optional[str] = None
        self.client = httpx.Client(timeout=15.0)

    def _get_headers(self, authenticated: bool = True) -> Dict[str, str]:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "product": "llu.android",
            "version": self.api_version,
            "Accept": "application/json",
            "Content-Type": "application/json",
            "cache-control": "no-cache",
        }
        if authenticated and self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        if self.account_id:
            account_hash = hashlib.sha256(self.account_id.encode("utf-8")).hexdigest()
            headers["Account-Id"] = account_hash
        return headers

    def authenticate(self, retry_count: int = 0) -> LibreAuthResult:
        """Authenticate user credentials with LibreLinkUp API with auto-region redirect handling."""
        if not self.email or not self.password:
            return LibreAuthResult(success=False, error_message="E-Mail oder Passwort fehlt.")

        payload = {
            "email": self.email,
            "password": self.password,
        }

        login_url = f"{self.base_url}/llu/auth/login"

        try:
            response = self.client.post(
                login_url,
                json=payload,
                headers=self._get_headers(authenticated=False),
            )

            if response.status_code == 200:
                data = response.json()
                
                # Check for region redirect
                if data.get("data", {}).get("redirect") is True:
                    new_region = data.get("data", {}).get("region", "de").lower()
                    logger.info(f"Abbott requested redirect to region: {new_region}")
                    if new_region in REGIONAL_ENDPOINTS and retry_count < 3:
                        self.region = new_region
                        self.base_url = REGIONAL_ENDPOINTS[new_region]
                        return self.authenticate(retry_count=retry_count + 1)

                # Check if minimumVersion update is needed
                if data.get("status") == 920:
                    min_ver = data.get("data", {}).get("minimumVersion")
                    if min_ver and retry_count < 3:
                        self.api_version = min_ver
                        return self.authenticate(retry_count=retry_count + 1)

                auth_ticket = data.get("data", {}).get("authTicket", {})
                user = data.get("data", {}).get("user", {})
                self.token = auth_ticket.get("token")
                self.account_id = user.get("id")
                expires = auth_ticket.get("expires")

                if not self.token:
                    return LibreAuthResult(
                        success=False,
                        error_message="Kein Auth-Token in Antwort erhalten.",
                    )

                return LibreAuthResult(
                    success=True,
                    token=self.token,
                    account_id=self.account_id,
                    expires_at=expires,
                )

            elif response.status_code in (401, 403):
                # Check if 403 was due to minimumVersion requirement
                try:
                    err_json = response.json()
                    if err_json.get("status") == 920 or "minimumVersion" in err_json.get("data", {}):
                        min_ver = err_json.get("data", {}).get("minimumVersion", "4.16.0")
                        if retry_count < 3:
                            self.api_version = min_ver
                            return self.authenticate(retry_count=retry_count + 1)
                except Exception:
                    pass

                return LibreAuthResult(
                    success=False,
                    error_message="Ungültige Anmeldedaten (E-Mail oder Passwort falsch).",
                )
            else:
                return LibreAuthResult(
                    success=False,
                    error_message=f"HTTP-Fehler {response.status_code}: {response.text[:200]}",
                )

        except httpx.RequestError as exc:
            logger.error(f"Network error during authentication: {exc}")
            return LibreAuthResult(
                success=False,
                error_message=f"Netzwerkfehler: Verbindung zu {self.base_url} fehlgeschlagen.",
            )
        except Exception as exc:
            logger.error(f"Unexpected error during auth: {exc}")
            return LibreAuthResult(
                success=False,
                error_message=f"Unerwarteter Fehler: {str(exc)}",
            )

    def get_connections(self) -> List[Dict[str, Any]]:
        """Retrieve list of connected patients (sensors)."""
        if not self.token:
            auth_res = self.authenticate()
            if not auth_res.success:
                raise RuntimeError(auth_res.error_message)

        url = f"{self.base_url}/llu/connections"
        try:
            response = self.client.get(url, headers=self._get_headers(authenticated=True))
            
            # Check for version update requirement
            if response.status_code == 403:
                try:
                    err_json = response.json()
                    min_ver = err_json.get("data", {}).get("minimumVersion")
                    if min_ver:
                        self.api_version = min_ver
                        self.token = None  # Force re-auth with new version
                        auth_res = self.authenticate()
                        if not auth_res.success:
                            raise RuntimeError(auth_res.error_message)
                        response = self.client.get(url, headers=self._get_headers(authenticated=True))
                except Exception:
                    pass

            if response.status_code in (401, 403):
                # Token expired, re-authenticate and retry once
                self.token = None
                auth_res = self.authenticate()
                if not auth_res.success:
                    raise RuntimeError(auth_res.error_message)
                response = self.client.get(url, headers=self._get_headers(authenticated=True))

            if response.status_code == 200:
                data = response.json()
                connections = data.get("data", [])
                return connections
            else:
                raise RuntimeError(f"Fehler beim Abrufen der Verbindungen ({response.status_code}): {response.text[:200]}")
        except Exception as e:
            logger.error(f"Error fetching connections: {e}")
            raise

    def get_latest_reading(self, patient_id: Optional[str] = None) -> Tuple[GlucoseReading, Optional[SensorInfo]]:
        """
        Fetch the latest glucose reading and active sensor info.
        If patient_id is not specified, uses the first available connection.
        """
        connections = self.get_connections()
        if not connections:
            raise RuntimeError("Keine verbundenen FreeStyle Libre Geräte gefunden. Bitte in der LibreLink App Einladung als Follower prüfen.")

        target_conn = None
        if patient_id:
            for conn in connections:
                if conn.get("patientId") == patient_id:
                    target_conn = conn
                    break
        
        if not target_conn:
            target_conn = connections[0]

        self.patient_id = target_conn.get("patientId", "")
        f_name = target_conn.get("firstName", "")
        l_name = target_conn.get("lastName", "")
        self.patient_name = f"{f_name} {l_name}".strip() or "Konrad"

        # Try to get latest reading from connection object or fetch graph endpoint
        glucose_data = target_conn.get("glucoseMeasurement") or target_conn.get("glucoseItem") or {}
        sensor_data = target_conn.get("sensor", {})

        # If glucoseMeasurement is empty on connection, fetch graph endpoint
        if not glucose_data or "ValueInMgPerDl" not in glucose_data:
            graph_url = f"{self.base_url}/llu/connections/{self.patient_id}/graph"
            resp = self.client.get(graph_url, headers=self._get_headers(authenticated=True))
            if resp.status_code == 200:
                g_json = resp.json().get("data", {})
                glucose_data = (
                    g_json.get("connection", {}).get("glucoseMeasurement")
                    or g_json.get("connection", {}).get("glucoseItem")
                    or {}
                )
                if not sensor_data:
                    sensor_data = g_json.get("connection", {}).get("sensor", {})

        if not glucose_data:
            raise RuntimeError("Keine aktuellen Blutzuckerdaten in der LibreLinkUp-Antwort vorhanden.")

        # Extract values
        val_mgdl = float(glucose_data.get("ValueInMgPerDl", 0.0))
        # Direct mmol/L value if provided by Abbott, else convert
        val_mmol = float(glucose_data.get("Value", round(val_mgdl / 18.0182, 1)))

        trend_id = int(glucose_data.get("TrendArrow", 0))
        trend_sym, trend_desc_en, trend_desc_de = TREND_ARROWS.get(
            trend_id, ("—", "Not determined", "Nicht ermittelt")
        )

        ts_str = glucose_data.get("Timestamp", "")
        parsed_ts = self._parse_timestamp(ts_str)

        color_code = int(glucose_data.get("MeasurementColor", 1))

        reading = GlucoseReading(
            value_mgdl=val_mgdl,
            value_mmol=val_mmol,
            trend_arrow_id=trend_id,
            trend_symbol=trend_sym,
            trend_description_de=trend_desc_de,
            trend_description_en=trend_desc_en,
            timestamp=parsed_ts,
            is_high=bool(glucose_data.get("isHigh", False)),
            is_low=bool(glucose_data.get("isLow", False)),
            measurement_color=color_code,
            patient_id=self.patient_id,
            patient_name=self.patient_name,
            sensor_serial=sensor_data.get("sn") or sensor_data.get("serialNumber") or "FreeStyle Libre 3",
            raw_data=glucose_data,
        )

        sensor_info = None
        if sensor_data:
            sn = sensor_data.get("sn") or sensor_data.get("serialNumber") or "FreeStyle Libre 3"
            dev_name = sensor_data.get("device", "FreeStyle Libre 3")
            sensor_info = SensorInfo(
                serial_number=sn,
                device_name=dev_name,
                activation_date=None,
                expiration_date=None,
                days_remaining=None,
                is_active=True,
            )

        return reading, sensor_info

    def get_historical_graph(self, patient_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Fetch past 12-24 hours historical readings graph array."""
        pid = patient_id or self.patient_id
        if not pid:
            self.get_connections()
            pid = self.patient_id

        if not pid:
            return []

        url = f"{self.base_url}/llu/connections/{pid}/graph"
        try:
            response = self.client.get(url, headers=self._get_headers(authenticated=True))
            if response.status_code == 200:
                data = response.json()
                graph_data = data.get("data", {}).get("graphData", [])
                return graph_data
            return []
        except Exception as e:
            logger.error(f"Error fetching historical graph: {e}")
            return []

    def _parse_timestamp(self, ts_str: str) -> datetime.datetime:
        """Parse various timestamp formats returned by Abbott API."""
        if not ts_str:
            return datetime.datetime.now()

        formats = [
            "%m/%d/%Y %I:%M:%S %p",
            "%m/%d/%Y %H:%M:%S",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%d %H:%M:%S",
        ]
        clean_str = ts_str.split(".")[0]
        for fmt in formats:
            try:
                return datetime.datetime.strptime(clean_str, fmt)
            except ValueError:
                continue

        try:
            return datetime.datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        except Exception:
            return datetime.datetime.now()

    def close(self) -> None:
        """Close HTTP client session."""
        self.client.close()
