import os
import sys

# Ensure local imports work when packaged/launched outside this folder.
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

from helper_functions import camera_record, fetch_scan_state, stitch_video
import threading
import time
import cv2
import torch
from PIL import Image
# PyInstaller can miss these symbols from `transformers.__init__` exports,
# so import from the concrete modules.
from transformers.models.lighton_ocr.modeling_lighton_ocr import (
    LightOnOcrForConditionalGeneration,
)
from transformers.models.lighton_ocr.processing_lighton_ocr import LightOnOcrProcessor

_ocr_bundle = None


def _ensure_writable_workdir() -> str:
    """
    When launched as a double-clicked macOS app, the working directory can be
    unpredictable. Use a stable writable folder so recordings/outputs end up
    somewhere the user can find.
    """
    out_dir = os.path.join(os.path.expanduser("~"), "Documents", "mvb_sw")
    os.makedirs(out_dir, exist_ok=True)
    try:
        os.chdir(out_dir)
    except OSError:
        # If chdir fails for any reason, fall back to current directory.
        pass
    return out_dir


def get_ocr():
    """
    Lazily load the LightOn OCR model once, then reuse it.
    """
    global _ocr_bundle
    if _ocr_bundle is None:
        device = (
            "mps"
            if torch.backends.mps.is_available()
            else "cuda"
            if torch.cuda.is_available()
            else "cpu"
        )
        dtype = torch.float32 if device == "mps" else torch.bfloat16
        model = LightOnOcrForConditionalGeneration.from_pretrained(
            "lightonai/LightOnOCR-2-1B-ocr-soup", torch_dtype=dtype
        ).to(device)
        processor = LightOnOcrProcessor.from_pretrained("lightonai/LightOnOCR-2-1B-ocr-soup")
        _ocr_bundle = (model, processor, device, dtype)
    return _ocr_bundle


def ocr_image(image_path: str) -> str:
    model, processor, device, dtype = get_ocr()

    image = Image.open(image_path).convert("RGB")
    conversation = [{"role": "user", "content": [{"type": "image", "image": image}]}]

    inputs = processor.apply_chat_template(
        conversation,
        add_generation_prompt=True,
        tokenize=True,
        return_dict=True,
        return_tensors="pt",
    )
    inputs = {
        k: v.to(device=device, dtype=dtype) if v.is_floating_point() else v.to(device)
        for k, v in inputs.items()
    }

    output_ids = model.generate(**inputs, max_new_tokens=1024)
    generated_ids = output_ids[0, inputs["input_ids"].shape[1] :]
    return processor.decode(generated_ids, skip_special_tokens=True)


URL = "http://192.168.55.39/stream"
SCAN_STATE_URL = "http://192.168.55.39:81/scan_state"
CROP_W = 250
CROP_H = 40
record_flag = threading.Event()
recording_done = threading.Event()   # signaled once the video file is fully written

# Make output files land in a stable writable place.
_WORKDIR = _ensure_writable_workdir()


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
                text = ocr_image("stitched_result.png")
                print(text)

        last_pressed = pressed
        time.sleep(0.1)



threading.Thread(target=esp_trigger_listener, daemon=True).start() # daemon=true, means that the thread will be killed/stopped if tha main.py script reaches its end
                                                                    #in this case, when camera_record dies for e.g. due to hitting q
                                                                    # you can keep it running in the background by setting daemon=false (thread runs until it finishes on its own)
camera_record(URL, crop_w=CROP_W, crop_h=CROP_H, record_flag=record_flag, recording_done=recording_done) # cant register that as a thread cuz im using camera preview in another file?