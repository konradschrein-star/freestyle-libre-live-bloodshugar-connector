"""
Unit tests for LibreClient with mock responses
"""

import unittest
from unittest.mock import patch, MagicMock
from src.libre_client import LibreClient, GlucoseReading


class TestLibreClient(unittest.TestCase):
    def setUp(self):
        self.client = LibreClient(
            email="test@example.com",
            password="secretpassword",
            region="eu",
        )

    def tearDown(self):
        self.client.close()

    @patch("httpx.Client.post")
    def test_authenticate_success(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "status": 0,
            "data": {
                "user": {"id": "user-123"},
                "authTicket": {
                    "token": "jwt-token-xyz",
                    "expires": 1789999999,
                },
                "redirect": False,
            },
        }
        mock_post.return_value = mock_resp

        res = self.client.authenticate()
        self.assertTrue(res.success)
        self.assertEqual(res.token, "jwt-token-xyz")
        self.assertEqual(res.account_id, "user-123")

    @patch("httpx.Client.get")
    @patch("httpx.Client.post")
    def test_get_latest_reading_success(self, mock_post, mock_get):
        # Auth mock
        mock_auth_resp = MagicMock()
        mock_auth_resp.status_code = 200
        mock_auth_resp.json.return_value = {
            "status": 0,
            "data": {
                "user": {"id": "u1"},
                "authTicket": {"token": "tok1", "expires": 1799999999},
            },
        }
        mock_post.return_value = mock_auth_resp

        # Connections mock
        mock_conn_resp = MagicMock()
        mock_conn_resp.status_code = 200
        mock_conn_resp.json.return_value = {
            "status": 0,
            "data": [
                {
                    "patientId": "pat-001",
                    "firstName": "Konrad",
                    "lastName": "Schrein",
                    "glucoseMeasurement": {
                        "ValueInMgPerDl": 115,
                        "TrendArrow": 4,  # Rising ↑
                        "Timestamp": "8/22/2026 5:45:00 AM",
                        "MeasurementColor": 1,
                        "IsHigh": False,
                        "IsLow": False,
                    },
                    "sensor": {
                        "sn": "0030589139",
                        "device": "FreeStyle Libre 3",
                    },
                }
            ],
        }
        mock_get.return_value = mock_conn_resp

        reading, sensor = self.client.get_latest_reading()
        self.assertEqual(reading.value_mgdl, 115.0)
        self.assertEqual(reading.value_mmol, 6.4)
        self.assertEqual(reading.trend_symbol, "↑")
        self.assertEqual(reading.patient_name, "Konrad Schrein")
        self.assertEqual(reading.status_label_de, "Normal")
        self.assertIsNotNone(sensor)
        self.assertEqual(sensor.serial_number, "0030589139")


if __name__ == "__main__":
    unittest.main()
