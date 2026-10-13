import cv2
import numpy as np

from wildlife_perception.opencv_px4_detector import orange_blob


def test_orange_blob_pixel_and_empty_image():
    frame = np.zeros((200, 200, 3), dtype=np.uint8)
    assert orange_blob(frame, 250.) is None
    cv2.circle(frame, (135, 70), 20, (0, 110, 255), -1)
    u, v, area = orange_blob(frame, 250.)
    assert abs(u - 135) < 1
    assert abs(v - 70) < 1
    assert area > 1000
    assert orange_blob(frame, 2000.) is None
