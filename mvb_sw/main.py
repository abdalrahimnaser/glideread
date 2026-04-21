from helper_functions import camera_record, fetch_scan_state, stitch_video
import threading
from notion_test import add_row_to_notion
import time
import cv2
import os

# PaddleOCRVL uses PaddleX pipelines/models which may attempt to probe remote
# model hosters at startup; for packaged/offline scenarios we disable that probe.
os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")

from paddleocr import PaddleOCRVL

pipeline = None


def get_pipeline():
    global pipeline
    if pipeline is None:
        pipeline = PaddleOCRVL()
    return pipeline


URL = "http://192.168.55.39/stream"
SCAN_STATE_URL = "http://192.168.55.39:81/scan_state"
CROP_W = 250
CROP_H = 40
record_flag = threading.Event()
recording_done = threading.Event()   # signaled once the video file is fully written


def esp_trigger_listener():
    """
    Poll ESP32 /scan_state and behave like a momentary push button:
    - press (button_pressed=true): start recording
    - release (button_pressed=false): stop recording then run OCR
    """
    last_pressed = None
    print(f"Polling ESP scan state at {SCAN_STATE_URL}")
    while True:
        _counter, pressed = fetch_scan_state(SCAN_STATE_URL)
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
                result = stitch_video('roi_capture.mp4')
                cv2.imwrite("stitched_result.png", result)
                ocr_result = get_pipeline().predict("stitched_result.png")
                text = ocr_result[0]['parsing_res_list'][0].content
                print(text)
                # add_row_to_notion(text, "Done")

        last_pressed = pressed
        time.sleep(0.1)



threading.Thread(target=esp_trigger_listener, daemon=True).start() # daemon=true, means that the thread will be killed/stopped if tha main.py script reaches its end
                                                                    #in this case, when camera_record dies for e.g. due to hitting q
                                                                    # you can keep it running in the background by setting daemon=false (thread runs until it finishes on its own)
camera_record(URL, crop_w=CROP_W, crop_h=CROP_H, record_flag=record_flag, recording_done=recording_done) # cant register that as a thread cuz im using camera preview in another file?