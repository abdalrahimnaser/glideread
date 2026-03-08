import cv2
import threading


def camera_record(url, record_flag: threading.Event, recording_done: threading.Event = None):
    """Shows cropped feed. Records while record_flag is set."""
    cap = cv2.VideoCapture(url)
    if not cap.isOpened():
        print("Error: Could not open stream.")
        exit()

    fw, fh = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    x1, y1 = (fw - 300) // 2, (fh - 80) // 2
    x2, y2 = x1 + 300, y1 + 80

    out = None
    recording = False

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        roi = cv2.flip(frame, 1)[y1:y2, x1:x2]

        should_record = record_flag.is_set()

        if should_record and not recording:
            out = cv2.VideoWriter('roi_capture.mp4', cv2.VideoWriter_fourcc(*'mp4v'), 20.0, (300, 80))
            recording = True
            print("Recording started")
        elif not should_record and recording:
            recording = False
            out.release()
            out = None
            print("Recording stopped")
            if recording_done:
                recording_done.set()

        if recording and out:
            out.write(roi)

        cv2.imshow("Feed", roi)
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    if out:
        out.release()
    cv2.destroyAllWindows()
