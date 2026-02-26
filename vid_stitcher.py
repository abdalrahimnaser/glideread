
import cv2
import numpy as np
import pytesseract

def is_blurry(image, threshold=100.0):
    """
    Calculates the Laplacian variance of the image to detect blur.
    Returns True if the variance is below the threshold (blurry), False otherwise.
    """
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    focus_measure = cv2.Laplacian(gray, cv2.CV_64F).var()
    return focus_measure < threshold, focus_measure

def stitch_panorama(video_path, frame_drop_factor=5, max_frames=None, blur_threshold=100.0):
    cap = cv2.VideoCapture(video_path)
    frames = []
    frame_count = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        # We can drop fewer frames initially (e.g., every 5th) because we filter by blur
        if frame_count % frame_drop_factor == 0:
            
            # QUALITY OPTIMIZATION 1: Check for motion blur before keeping the frame
            blurry, focus = is_blurry(frame, blur_threshold)
            
            if not blurry:
                frames.append(frame)
                # Optional: Uncomment the next line to see the focus scores in your terminal
                # print(f"Kept frame (Focus score: {focus:.2f})")
            else:
                pass 
                # print(f"Dropped blurry frame (Focus score: {focus:.2f})")
                
            if max_frames and len(frames) >= max_frames:
                break
        
        frame_count += 1
    
    cap.release()
    
    if len(frames) < 2:
        print("Not enough sharp frames found to stitch! Try lowering the blur_threshold.")
        return
    
    stitcher = cv2.Stitcher.create(cv2.Stitcher_SCANS)
    status, result = stitcher.stitch(frames)
    
    if status == cv2.Stitcher_OK:
        gray_result = cv2.cvtColor(result, cv2.COLOR_BGR2GRAY)
        
        # QUALITY OPTIMIZATION 2: Apply CLAHE to safely boost text contrast
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        enhanced_result = clahe.apply(gray_result)
        
        cv2.imshow('Panorama', enhanced_result)
        
        # Configure Tesseract
        custom_config = r'--oem 3 --psm 6'
        text = pytesseract.image_to_string(enhanced_result, config=custom_config)
        
        print("--- Extracted Text ---")
        print(text)
        
        cv2.imwrite('panorama_result.jpg', enhanced_result)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
    else:
        print(f"Stitching failed with status: {status}")

# Example usage
video_path = "vid2.mp4"

# NOTE: I changed frame_drop_factor to 5. Since we are rejecting blurry frames, 
# we need to look at more frames overall to find enough good ones.
stitch_panorama(video_path, frame_drop_factor=1, max_frames=15, blur_threshold=65.0)
