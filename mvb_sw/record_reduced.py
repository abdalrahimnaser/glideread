import cv2
import threading


def camera_record(url, record_flag: threading.Event, recording_done: threading.Event = None):
    """Shows stream (optional center crop). Records while record_flag is set."""
    cap = cv2.VideoCapture(url)
    if not cap.isOpened():
        print("Error: Could not open stream.")
        exit()

    # Center crop: set either to an int to crop, or None to use full flipped frame.
    crop_w, crop_h = None, None    # Example (MVB strip): crop_w, crop_h = 300, 80

    out = None
    recording = False

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame = cv2.flip(frame, -1)
        fh, fw = frame.shape[:2]
        if crop_w is None or crop_h is None:
            roi = frame
        else:
            x1 = max(0, (fw - crop_w) // 2)
            y1 = max(0, (fh - crop_h) // 2)
            roi = frame[y1 : y1 + crop_h, x1 : x1 + crop_w]

        rw, rh = roi.shape[1], roi.shape[0]

        should_record = record_flag.is_set()

        if should_record and not recording:
            out = cv2.VideoWriter(
                'roi_capture.mp4',
                cv2.VideoWriter_fourcc(*'mp4v'),
                20.0,
                (rw, rh),
            )
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