import cv2
import numpy as np

# --- SETTINGS ---
STREAM_URL = "http://192.168.116.207:81/stream" 

def nothing(x):
    pass

cap = cv2.VideoCapture(STREAM_URL)
if not cap.isOpened():
    print("Error: Could not open stream.")
    exit()

frame_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
frame_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

cv2.namedWindow('Master Stream')

cv2.createTrackbar('Box Width', 'Master Stream', 300, frame_w, nothing)
cv2.createTrackbar('Box Height', 'Master Stream', 200, frame_h, nothing)

out = None
recording = False
snap_count = 0  # Initialize the counter here

print("Controls:")
print("  - 'r' to START/STOP recording")
print("  - 's' to SNAP a picture (snap_N.png)")
print("  - 'q' to QUIT")

while True:
    ret, frame = cap.read()
    if not ret:
        break
    
    frame = cv2.flip(frame, 1)

    bw = max(1, cv2.getTrackbarPos('Box Width', 'Master Stream'))
    bh = max(1, cv2.getTrackbarPos('Box Height', 'Master Stream'))

    x1 = (frame_w - bw) // 2
    y1 = (frame_h - bh) // 2
    x2, y2 = x1 + bw, y1 + bh

    roi = frame[y1:y2, x1:x2].copy()

    if recording and out is not None:
        out.write(roi)

    display_frame = frame.copy()
    color = (0, 0, 255) if recording else (0, 255, 0)
    cv2.rectangle(display_frame, (x1, y1), (x2, y2), color, 2)
    
    if recording:
        cv2.circle(display_frame, (30, 30), 10, (0, 0, 255), -1)
        cv2.putText(display_frame, "RECORDING", (50, 40), 
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

    cv2.imshow('Master Stream', display_frame)
    cv2.imshow('ROI Preview', roi)

    key = cv2.waitKey(1) & 0xFF
    
    # --- SEQUENTIAL SNAPSHOT LOGIC ---
    if key == ord('s'):
        snap_count += 1  # Increment the number
        filename = f"snap_{snap_count}.png"
        cv2.imwrite(filename, roi)
        print(f"Snapshot saved as {filename}")

    elif key == ord('r'):
        if not recording:
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            # Note: If you change box size while recording, 
            # the video file might be corrupted. 
            out = cv2.VideoWriter('roi_capture.mp4', fourcc, 20.0, (bw, bh))
            recording = True
            print("Started Recording...")
        else:
            recording = False
            out.release()
            out = None
            print("Recording Saved to roi_capture.mp4")

    elif key == ord('q'):
        break

cap.release()
if out: out.release()
cv2.destroyAllWindows()