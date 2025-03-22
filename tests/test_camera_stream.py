import unittest
import os
import json
import cv2
import numpy as np
from unittest.mock import patch, MagicMock
import camera_stream
from datetime import datetime

class TestCameraStream(unittest.TestCase):
    def setUp(self):
        camera_stream.app.config['TESTING'] = True
        self.app = camera_stream.app.test_client()
        self.test_frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        
    def tearDown(self):
        # Clean up any test photos or videos
        for f in os.listdir('photos'):
            if f.startswith('photo_test_'):
                os.remove(os.path.join('photos', f))
        for f in os.listdir('videos'):
            if f.startswith('video_test_'):
                os.remove(os.path.join('videos', f))

    def test_index_route(self):
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'camera_stream_index.html', response.data)

    @patch('fermia_camera.get_image')
    def test_capture_frames(self, mock_get_image):
        mock_get_image.return_value = self.test_frame
        with patch.object(camera_stream, 'frame', None):
            camera_stream.capture_frames()
            # Since capture_frames runs in an infinite loop, we just test one iteration
            mock_get_image.assert_called_once()
            self.assertIsNotNone(camera_stream.frame)

    def test_video_feed_route(self):
        response = self.app.get('/video_feed')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, 'multipart/x-mixed-replace; boundary=frame')

    @patch.object(camera_stream, 'frame')
    def test_take_photo(self, mock_frame):
        mock_frame = self.test_frame
        response = self.app.get('/take_photo')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('photo_', data['filename'])
        
    @patch.object(camera_stream, 'frame')
    def test_take_photo_no_frame(self, mock_frame):
        mock_frame = None
        response = self.app.get('/take_photo')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertEqual(data['message'], 'No camera frame available')

    @patch.object(camera_stream, 'frame')
    def test_start_recording(self, mock_frame):
        mock_frame = self.test_frame
        response = self.app.get('/start_recording')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertTrue(camera_stream.is_recording)
        self.assertIsNotNone(camera_stream.video_writer)

    def test_stop_recording_when_not_recording(self):
        camera_stream.is_recording = False
        response = self.app.get('/stop_recording')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertEqual(data['message'], 'Not currently recording')

if __name__ == '__main__':
    unittest.main()
