"""
Unit tests for Local SQLite Database and Analytics
"""

import datetime
import os
import unittest
from pathlib import Path
import tempfile

from src.storage import DatabaseManager
from src.libre_client import GlucoseReading
from src.config import GlucoseTargetRanges


class TestDatabaseManager(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_blood_sugar.db"
        self.db_mgr = DatabaseManager(self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_insert_and_get_latest(self):
        now = datetime.datetime.now()
        reading = GlucoseReading(
            value_mgdl=118.0,
            value_mmol=6.5,
            trend_arrow_id=3,
            trend_symbol="→",
            trend_description_de="Stabil",
            trend_description_en="Stable",
            timestamp=now,
            is_high=False,
            is_low=False,
            measurement_color=1,
            patient_id="p123",
            patient_name="Konrad",
            sensor_serial="SN9999",
            raw_data={"test": 123},
        )
        inserted = self.db_mgr.insert_reading(reading)
        self.assertTrue(inserted)

        # Retrieve latest
        latest = self.db_mgr.get_latest_reading()
        self.assertIsNotNone(latest)
        self.assertEqual(latest.value_mgdl, 118.0)
        self.assertEqual(latest.value_mmol, 6.5)
        self.assertEqual(latest.trend_symbol, "→")
        self.assertEqual(latest.patient_name, "Konrad")

    def test_statistics_and_tir(self):
        base_time = datetime.datetime.now()
        readings = [
            GlucoseReading(
                value_mgdl=val,
                value_mmol=round(val / 18.0182, 1),
                trend_arrow_id=3,
                trend_symbol="→",
                trend_description_de="Stabil",
                trend_description_en="Stable",
                timestamp=base_time - datetime.timedelta(minutes=i * 5),
                is_high=val > 180,
                is_low=val < 70,
                measurement_color=1 if 70 <= val <= 180 else (2 if val > 180 else 3),
                patient_id="p1",
                patient_name="Konrad",
            )
            for i, val in enumerate([100.0, 120.0, 140.0, 80.0, 200.0])
        ]
        self.db_mgr.insert_batch(readings)

        stats = self.db_mgr.get_statistics(hours=24, targets=GlucoseTargetRanges())
        self.assertEqual(stats["count"], 5)
        self.assertEqual(stats["average_mgdl"], 128.0)
        self.assertEqual(stats["min_mgdl"], 80.0)
        self.assertEqual(stats["max_mgdl"], 200.0)
        # 4 out of 5 in range (80%)
        self.assertEqual(stats["time_in_range"]["target_percent"], 80.0)
        # 1 out of 5 high (20%)
        self.assertEqual(stats["time_in_range"]["high_percent"], 20.0)


if __name__ == "__main__":
    unittest.main()
