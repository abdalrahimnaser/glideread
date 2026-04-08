# import cv2
# import numpy as np

# cap = cv2.VideoCapture("http://192.168.125.207:81/stream")
# frames = []
# capturing = False
# frame_count = 0

# while True:
#     ret, frame = cap.read()

#     if not ret:
#         print("Failed to grab frame")
#         break

#     display_frame = frame.copy()
#     status = "CAPTURING" if capturing else "IDLE"
#     cv2.putText(display_frame, status, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0) if capturing else (0, 0, 255), 2)
#     cv2.imshow('ESP32 Stream', display_frame)

#     key = cv2.waitKey(1) & 0xFF
#     if key == ord('s'):
#         capturing = not capturing
#         print("Capturing" if capturing else "Stopped capturing")
#     elif key == ord('q'):
#         break
#     elif key == ord('r') and frames:
#         stitcher = cv2.Stitcher_create()
#         status, result = stitcher.stitch(frames)
#         if status == cv2.Stitcher_OK:
#             cv2.imshow('Panorama', result)
#             cv2.waitKey(0)
#         else:
#             print("Stitching failed")
#         frames = []

#     if capturing:
#         frame_count += 1
#         if frame_count % 5 == 0:
#             frames.append(frame)

# cap.release()
# cv2.destroyAllWindows()

import cv2
import urllib.request
import numpy as np

stream_url = 'http://192.168.125.207:81/stream'
stream = urllib.request.urlopen(stream_url)
bytes_data = b''

# Toggle states
is_stitching = False
full_scan = None

def get_frame():
    global bytes_data
    try:
        # Read a larger chunk to ensure we get a full frame
        bytes_data += stream.read(4096) 
        
        # Look for JPEG Start of Image (SOI) and End of Image (EOI)
        a = bytes_data.find(b'\xff\xd8')
        b = bytes_data.find(b'\xff\xd9')
        
        if a != -1 and b != -1:
            jpg = bytes_data[a:b+2]
            bytes_data = bytes_data[b+2:]
            
            # CRITICAL: Convert to numpy array and check if empty
            raw = np.frombuffer(jpg, dtype=np.uint8)
            if raw.size == 0:
                return None
                
            img = cv2.imdecode(raw, cv2.IMREAD_GRAYSCALE)
            
            # If imdecode fails (returns None), return None instead of crashing
            if img is None:
                return None
                
            return img
    except Exception as e:
        print(f"Stream error: {e}")
    return None

print("S: Start/Stop Stitching | C: Clear | Q: Quit")

while True:
    frame = get_frame()
    if frame is None: continue

    # 1. Prepare the preview frame
    preview = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
    
    # 2. Logic to handle the 's' key toggle
    key = cv2.waitKey(1) & 0xFF
    if key == ord('s'):
        is_stitching = not is_stitching # Flip the switch
        status = "STARTED" if is_stitching else "STOPPED"
        print(f"Stitching {status}")

    # 3. Perform stitching if the toggle is ON
    if is_stitching:
        # Add a red "Recording" dot to the preview
        cv2.circle(preview, (30, 30), 10, (0, 0, 255), -1)
        
        # Grab the slit and append
        h, w = frame.shape
        slit = frame[:, w//2 : w//2 + 10]
        if full_scan is None:
            full_scan = slit
        else:
            full_scan = np.hstack((full_scan, slit))
        
        cv2.imshow("Resulting Scan", full_scan)

    # 4. Utilities
    if key == ord('c'):
        full_scan = None
        is_stitching = False
        print("Cleared.")
    elif key == ord('q'):
        if full_scan is not None:
            cv2.imwrite("final_text_strip.jpg", full_scan)
        break

    cv2.imshow("ESP32 Scanner Feed", preview)

cv2.destroyAllWindows()