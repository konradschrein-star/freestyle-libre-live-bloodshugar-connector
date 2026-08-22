"""
Unit tests for Dynamic Tray Icon Generator
"""

import unittest
from PIL import Image
from src.tray_icon import create_glucose_icon, create_offline_icon, get_status_color, COLOR_GREEN, COLOR_RED, COLOR_YELLOW


class TestTrayIcon(unittest.TestCase):
    def test_create_glucose_icon_mmol(self):
        # Test normal in-range in mmol/L
        img = create_glucose_icon("6.4", "→", bg_color=COLOR_GREEN, size=64)
        self.assertIsInstance(img, Image.Image)
        self.assertEqual(img.size, (64, 64))

        # Test high mmol/L reading with rising arrow
        img_high = create_glucose_icon("11.5", "↑", bg_color=COLOR_YELLOW, size=64)
        self.assertIsInstance(img_high, Image.Image)
        self.assertEqual(img_high.size, (64, 64))

        # Test low mmol/L reading with urgent arrow
        img_low = create_glucose_icon("3.2", "↓↓", bg_color=COLOR_RED, size=64)
        self.assertIsInstance(img_low, Image.Image)
        self.assertEqual(img_low.size, (64, 64))

    def test_create_glucose_icon_mgdl(self):
        # Test standard mg/dL integer
        img = create_glucose_icon("115", "↗", bg_color=COLOR_GREEN, size=64)
        self.assertIsInstance(img, Image.Image)
        self.assertEqual(img.size, (64, 64))

    def test_status_color_thresholds(self):
        self.assertEqual(get_status_color(110), COLOR_GREEN)
        self.assertEqual(get_status_color(210), COLOR_YELLOW)
        self.assertEqual(get_status_color(270), COLOR_RED)
        self.assertEqual(get_status_color(45), COLOR_RED)
        self.assertEqual(get_status_color(0), (100, 116, 139))


if __name__ == "__main__":
    unittest.main()
