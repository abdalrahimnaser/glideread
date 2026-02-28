
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

def stitch_panorama(video_path, frame_drop_factor=5, max_frames=None, blur_threshold=65.0):
    cap = cv2.VideoCapture(video_path)
    frames = []
    frame_count = 0
    
    # 1. Extraction Logic (Same as your original code)
    while True:
        ret, frame = cap.read()
        if not ret: break
        if frame_count % frame_drop_factor == 0:
            blurry, _ = is_blurry(frame, blur_threshold)
            if not blurry:
                frames.append(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)) # Process in Grayscale for speed
        if max_frames and len(frames) >= max_frames: break
        frame_count += 1
    cap.release()

    if len(frames) < 2:
        print("Not enough sharp frames.")
        return

    # 2. TEMPLATE MATCHING STITCHER (The New Part)
    # Start with the first frame as our base panorama
    panorama = frames[0]

    for i in range(1, len(frames)):
        curr_frame = frames[i]
        
        # Define the 'search' area: A strip from the right of our existing panorama
        # We assume the pen moves left-to-right.
        h, w = panorama.shape
        strip_width = int(w * 0.3)  # Use the right 30% of the panorama as a template
        template = panorama[:, w - strip_width:]

        # Find where this template exists in the NEW frame
        res = cv2.matchTemplate(curr_frame, template, cv2.TM_CCOEFF_NORMED)
        _, _, _, max_loc = cv2.minMaxLoc(res)

        # max_loc[0] is the x-coordinate in curr_frame where the overlap starts
        overlap_x = max_loc[0]
        
        # Extract the 'new' part of the current frame (everything to the right of the overlap)
        new_strip = curr_frame[:, overlap_x + strip_width:]
        
        # Glue it to the panorama
        panorama = np.hstack((panorama, new_strip))

    # 3. Final Post-Processing & OCR
    # Apply CLAHE to the final long strip
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
    enhanced_result = clahe.apply(panorama)

    # Show result (resized so it fits on screen)
    display_w = 1200
    display_h = int(enhanced_result.shape[0] * (display_w / enhanced_result.shape[1]))
    cv2.imshow('Fast Stitch Result', cv2.resize(enhanced_result, (display_w, display_h)))

    # OCR
    text = pytesseract.image_to_string(enhanced_result, config=r'--oem 3 --psm 6')
    print("--- Extracted Text ---")
    print(text)
    
    cv2.waitKey(0)
    cv2.destroyAllWindows()

# Example usage
video_path = "vid3.mp4"

# NOTE: I changed frame_drop_factor to 5. Since we are rejecting blurry frames, 
# we need to look at more frames overall to find enough good ones.
stitch_panorama(video_path, frame_drop_factor=1, max_frames=None, blur_threshold=65.0)