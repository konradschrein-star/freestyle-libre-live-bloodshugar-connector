"""
FreeStyle Libre Live Blood Sugar Connector - Storage & Analytics Module
100% Local SQLite Persistence and Analytics (GDPR/DSGVO Compliant).
"""

from __future__ import annotations
import csv
import datetime
import json
import math
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

from .config import GlucoseTargetRanges, get_app_data_dir
from .libre_client import GlucoseReading, TREND_ARROWS


class DatabaseManager:
    """Manages local SQLite database operations and analytical queries."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        if db_path is None:
            self.db_path = get_app_data_dir() / "blood_sugar.db"
        else:
            self.db_path = db_path

        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Create and return a configured SQLite connection."""
        conn = sqlite3.connect(str(self.db_path), timeout=10.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Initialize database tables and indexes."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = self._get_connection()
        try:
            with conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS glucose_readings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL UNIQUE,
                        value_mgdl REAL NOT NULL,
                        value_mmol REAL NOT NULL,
                        trend_arrow_id INTEGER,
                        trend_symbol TEXT,
                        color_code INTEGER,
                        is_high INTEGER DEFAULT 0,
                        is_low INTEGER DEFAULT 0,
                        patient_id TEXT,
                        patient_name TEXT,
                        sensor_serial TEXT,
                        raw_json TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    );
                """)

                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_glucose_timestamp 
                    ON glucose_readings(timestamp);
                """)
        finally:
            conn.close()

    def insert_reading(self, reading: GlucoseReading) -> bool:
        """Insert a single glucose reading. Returns True if inserted, False if duplicate."""
        ts_iso = reading.timestamp.isoformat()
        conn = self._get_connection()
        try:
            with conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR IGNORE INTO glucose_readings (
                        timestamp, value_mgdl, value_mmol, trend_arrow_id, trend_symbol,
                        color_code, is_high, is_low, patient_id, patient_name,
                        sensor_serial, raw_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    ts_iso,
                    reading.value_mgdl,
                    reading.value_mmol,
                    reading.trend_arrow_id,
                    reading.trend_symbol,
                    reading.measurement_color,
                    1 if reading.is_high else 0,
                    1 if reading.is_low else 0,
                    reading.patient_id,
                    reading.patient_name,
                    reading.sensor_serial,
                    json.dumps(reading.raw_data),
                ))
                return cursor.rowcount > 0
        finally:
            conn.close()

    def insert_batch(self, readings: List[GlucoseReading]) -> int:
        """Insert multiple readings in a single transaction. Returns number of new rows."""
        if not readings:
            return 0

        inserted = 0
        conn = self._get_connection()
        try:
            with conn:
                cursor = conn.cursor()
                for r in readings:
                    cursor.execute("""
                        INSERT OR IGNORE INTO glucose_readings (
                            timestamp, value_mgdl, value_mmol, trend_arrow_id, trend_symbol,
                            color_code, is_high, is_low, patient_id, patient_name,
                            sensor_serial, raw_json
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        r.timestamp.isoformat(),
                        r.value_mgdl,
                        r.value_mmol,
                        r.trend_arrow_id,
                        r.trend_symbol,
                        r.measurement_color,
                        1 if r.is_high else 0,
                        1 if r.is_low else 0,
                        r.patient_id,
                        r.patient_name,
                        r.sensor_serial,
                        json.dumps(r.raw_data),
                    ))
                    if cursor.rowcount > 0:
                        inserted += 1
            return inserted
        finally:
            conn.close()

    def get_latest_reading(self) -> Optional[GlucoseReading]:
        """Fetch the most recent reading from the database."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM glucose_readings 
                ORDER BY timestamp DESC 
                LIMIT 1
            """)
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_reading(row)
        finally:
            conn.close()

    def get_readings_since(self, since: datetime.datetime) -> List[GlucoseReading]:
        """Fetch all readings since a given timestamp."""
        since_iso = since.isoformat()
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM glucose_readings 
                WHERE timestamp >= ? 
                ORDER BY timestamp ASC
            """, (since_iso,))
            rows = cursor.fetchall()
            return [self._row_to_reading(row) for row in rows]
        finally:
            conn.close()

    def get_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent readings as structured dicts for web display or API."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT timestamp, value_mgdl, value_mmol, trend_symbol, color_code, is_high, is_low
                FROM glucose_readings 
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (limit,))
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()

    def get_statistics(
        self,
        hours: int = 24,
        targets: Optional[GlucoseTargetRanges] = None,
    ) -> Dict[str, Any]:
        """Calculate clinical glycemic metrics and Time in Range (TIR)."""
        if targets is None:
            targets = GlucoseTargetRanges()

        cutoff = datetime.datetime.now() - datetime.timedelta(hours=hours)
        readings = self.get_readings_since(cutoff)

        if not readings:
            return {
                "count": 0,
                "hours": hours,
                "average_mgdl": 0.0,
                "average_mmol": 0.0,
                "min_mgdl": 0.0,
                "max_mgdl": 0.0,
                "std_dev": 0.0,
                "cv_percent": 0.0,
                "estimated_hba1c": 0.0,
                "time_in_range": {
                    "very_low_percent": 0.0,
                    "low_percent": 0.0,
                    "target_percent": 0.0,
                    "high_percent": 0.0,
                    "very_high_percent": 0.0,
                },
            }

        values = [r.value_mgdl for r in readings]
        count = len(values)
        avg_mgdl = sum(values) / count
        avg_mmol = round(avg_mgdl / 18.0182, 1)
        min_mgdl = min(values)
        max_mgdl = max(values)

        # Standard Deviation
        variance = sum((x - avg_mgdl) ** 2 for x in values) / count if count > 1 else 0.0
        std_dev = math.sqrt(variance)
        cv_percent = (std_dev / avg_mgdl * 100) if avg_mgdl > 0 else 0.0

        # Estimated HbA1c formula (NGSP): eA1c (%) = (avg_mgdl + 46.7) / 28.7
        e_hba1c = (avg_mgdl + 46.7) / 28.7

        # Time in Range breakdown
        c_very_low = sum(1 for v in values if v < targets.very_low)
        c_low = sum(1 for v in values if targets.very_low <= v < targets.target_low)
        c_target = sum(1 for v in values if targets.target_low <= v <= targets.target_high)
        c_high = sum(1 for v in values if targets.target_high < v <= targets.high)
        c_very_high = sum(1 for v in values if v > targets.high)

        return {
            "count": count,
            "hours": hours,
            "average_mgdl": round(avg_mgdl, 1),
            "average_mmol": avg_mmol,
            "min_mgdl": round(min_mgdl, 1),
            "max_mgdl": round(max_mgdl, 1),
            "std_dev": round(std_dev, 1),
            "cv_percent": round(cv_percent, 1),
            "estimated_hba1c": round(e_hba1c, 1),
            "time_in_range": {
                "very_low_percent": round(c_very_low / count * 100, 1),
                "low_percent": round(c_low / count * 100, 1),
                "target_percent": round(c_target / count * 100, 1),
                "high_percent": round(c_high / count * 100, 1),
                "very_high_percent": round(c_very_high / count * 100, 1),
            },
        }

    def export_to_csv(self, file_path: Path) -> int:
        """Export all readings to standard CSV format. Returns number of rows exported."""
        conn = self._get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT timestamp, value_mgdl, value_mmol, trend_symbol, 
                       color_code, is_high, is_low, patient_name, sensor_serial
                FROM glucose_readings 
                ORDER BY timestamp ASC
            """)
            rows = cursor.fetchall()
        finally:
            conn.close()

        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Timestamp (ISO)", "Glucose (mg/dL)", "Glucose (mmol/L)",
                "Trend", "Color Code", "Is High", "Is Low", "Patient", "Sensor Serial"
            ])
            for r in rows:
                writer.writerow(list(r))

        return len(rows)

    def _row_to_reading(self, row: sqlite3.Row) -> GlucoseReading:
        """Convert SQLite row to GlucoseReading dataclass."""
        ts = datetime.datetime.fromisoformat(row["timestamp"])
        trend_id = row["trend_arrow_id"] or 0
        trend_sym, trend_desc_en, trend_desc_de = TREND_ARROWS.get(
            trend_id, ("—", "Not determined", "Nicht ermittelt")
        )
        raw_json_str = row["raw_json"]
        raw_dict = json.loads(raw_json_str) if raw_json_str else {}

        return GlucoseReading(
            value_mgdl=float(row["value_mgdl"]),
            value_mmol=float(row["value_mmol"]),
            trend_arrow_id=trend_id,
            trend_symbol=row["trend_symbol"] or trend_sym,
            trend_description_de=trend_desc_de,
            trend_description_en=trend_desc_en,
            timestamp=ts,
            is_high=bool(row["is_high"]),
            is_low=bool(row["is_low"]),
            measurement_color=row["color_code"] or 1,
            patient_id=row["patient_id"] or "",
            patient_name=row["patient_name"] or "",
            sensor_serial=row["sensor_serial"],
            raw_data=raw_dict,
        )
