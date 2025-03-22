import unittest
import os
import json
import cv2
import numpy as np
from unittest.mock import patch, MagicMock
import depth_stream
from datetime import datetime

class TestDepthStream(unittest.TestCase):
    def setUp(self):
        depth_stream.app.config['TESTING'] = True
        self.app = depth_stream.app.test_client()
        self.test_frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        
    def tearDown(self):
        # Clean up any test photos or videos
        for f in os.listdir('photos'):
            if f.startswith('depth_photo_test_'):
                os.remove(os.path.join('photos', f))
        for f in os.listdir('videos'):
            if f.startswith('depth_video_test_'):
                os.remove(os.path.join('videos', f))

    def test_index_route(self):
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'depth_stream_index.html', response.data)

    @patch('fermia_camera.get_depth_image')
    def test_capture_frames(self, mock_get_depth_image):
        mock_get_depth_image.return_value = self.test_frame
        with patch.object(depth_stream, 'frame', None):
            depth_stream.capture_frames()
            # Since capture_frames runs in an infinite loop, we just test one iteration
            mock_get_depth_image.assert_called_once()
            self.assertIsNotNone(depth_stream.frame)

    def test_video_feed_route(self):
        response = self.app.get('/video_feed')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.mimetype, 'multipart/x-mixed-replace; boundary=frame')

    @patch.object(depth_stream, 'frame')
    def test_take_photo(self, mock_frame):
        mock_frame = self.test_frame
        response = self.app.get('/take_photo')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertIn('depth_photo_', data['filename'])
        
    @patch.object(depth_stream, 'frame')
    def test_take_photo_no_frame(self, mock_frame):
        mock_frame = None
        response = self.app.get('/take_photo')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertEqual(data['message'], 'No camera frame available')

    @patch.object(depth_stream, 'frame')
    def test_start_recording(self, mock_frame):
        mock_frame = self.test_frame
        response = self.app.get('/start_recording')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        self.assertTrue(depth_stream.is_recording)
        self.assertIsNotNone(depth_stream.video_writer)

    def test_stop_recording_when_not_recording(self):
        depth_stream.is_recording = False
        response = self.app.get('/stop_recording')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertFalse(data['success'])
        self.assertEqual(data['message'], 'Not currently recording')

if __name__ == '__main__':
    unittest.main()
