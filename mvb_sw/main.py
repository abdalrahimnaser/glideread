"""
basically for now, the script is to do the following:
camera feed url
crop to 80*300 (no need to change automatically - keep that in the record-esp file for testing)
if the button r is pressed, start recording untill pressed again
save the video, do the ocr logic, print the text on screen.
=====
then ....
1) send this text to notion through their api.
2) replace the record/stop logic with a http message from the pen
3) app gui w/ config option like notion api key & pen set-up/connectivity

"""
from record_reduced import camera_record
from stitching_ocr import stitch_video_and_ocr
import threading
from notion_test import add_row_to_notion
import cv2
import json
import time
from typing import Optional
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError

URL = "http://192.168.55.43/stream"
SCAN_STATE_URL = "http://192.168.55.43:81/scan_state"

record_flag = threading.Event()
recording_done = threading.Event()   # signaled once the video file is fully written

def fetch_scan_state() -> tuple[Optional[int], Optional[bool]]:
    try:
        req = Request(SCAN_STATE_URL, method="GET")
        with urlopen(req, timeout=2.0) as resp:
            body = resp.read().decode("utf-8", errors="replace")
        data = json.loads(body)
        counter = int(data.get("trigger_counter", 0))
        pressed = bool(data.get("button_pressed", False))
        return counter, pressed
    except (
        URLError,
        HTTPError,
        TimeoutError,
        ConnectionResetError,
        OSError,
        ValueError,
        json.JSONDecodeError,
    ):
        return None, None


def process_once():
    print("Stitching and OCRing...")
    text, result = stitch_video_and_ocr('roi_capture.mp4')
    print(text)
    cv2.imwrite("stitched_result.png", result)
    # add_row_to_notion(text, "Done")


def esp_trigger_listener():
    """
    Poll ESP32 /scan_state and behave like a momentary push button:
    - press (button_pressed=true): start recording
    - release (button_pressed=false): stop recording then run OCR
    """
    last_pressed = None
    print(f"Polling ESP scan state at {SCAN_STATE_URL}")
    while True:
        _counter, pressed = fetch_scan_state()
        if pressed is None:
            time.sleep(0.25)
            continue

        if last_pressed is None:
            last_pressed = pressed
            time.sleep(0.1)
            continue

        # pressed edge -> start
        if (not last_pressed) and pressed:
            if not record_flag.is_set():
                recording_done.clear()
                record_flag.set()
                print("ESP button: PRESSED -> START recording")

        # released edge -> stop + process
        if last_pressed and (not pressed):
            if record_flag.is_set():
                record_flag.clear()
                print("ESP button: RELEASED -> STOP recording (waiting for file flush)")
                recording_done.wait()
                process_once()

        last_pressed = pressed

        time.sleep(0.1)

threading.Thread(target=esp_trigger_listener, daemon=True).start() # daemon=true, means that the thread will be killed/stopped if tha main.py script reaches its end
                                                            #in this case, when camera_record dies for e.g. due to hitting q
                                                            # you can keep it running in the background by setting daemon=false (thread runs until it finishes on its own)


camera_record(URL, record_flag, recording_done)