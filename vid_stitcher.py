import cv2
import numpy as np
import pytesseract

def stitch_panorama(video_path, frame_drop_factor=5, max_frames=None):
    """
    Extract frames from video, stitch them as panorama, and display result.
    frame_drop_factor: process every nth frame (5 = every 5th frame)
    max_frames: limit total frames to process (None = all)
    """
    cap = cv2.VideoCapture(video_path)
    frames = []
    frame_count = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        if frame_count % frame_drop_factor == 0:
            frames.append(cv2.resize(frame, (640, 480)))
            if max_frames and len(frames) >= max_frames:
                break
        
        frame_count += 1
    
    cap.release()
    
    if len(frames) < 2:
        print("Need at least 2 frames to stitch")
        return
    
    stitcher = cv2.Stitcher.create()
    status, result = stitcher.stitch(frames)
    
    if status == cv2.Stitcher_OK:
        cv2.imshow('Panorama', result)
        text = pytesseract.image_to_string(result)
        print(text)
        cv2.imwrite('panorama_result.jpg', result)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    else:
        print(f"Stitching failed with status: {status}")


video_path = "vid.mp4"
stitch_panorama(video_path, frame_drop_factor=15, max_frames=20)
