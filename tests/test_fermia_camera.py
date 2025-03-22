import unittest
from unittest.mock import patch, MagicMock
import fermia_camera
import numpy as np

class TestFermiaCamera(unittest.TestCase):
    def setUp(self):
        self.test_image = np.zeros((720, 1280, 3), dtype=np.uint8)

    @patch('fermia_camera.get_image')
    def test_get_image(self, mock_get_image):
        mock_get_image.return_value = self.test_image
        image = fermia_camera.get_image()
        self.assertIsNotNone(image)
        self.assertEqual(image.shape, (720, 1280, 3))
        mock_get_image.assert_called_once()

    @patch('fermia_camera.get_depth_image')
    def test_get_depth_image(self, mock_get_depth_image):
        mock_get_depth_image.return_value = self.test_image
        image = fermia_camera.get_depth_image()
        self.assertIsNotNone(image)
        self.assertEqual(image.shape, (720, 1280, 3))
        mock_get_depth_image.assert_called_once()

if __name__ == '__main__':
    unittest.main()
