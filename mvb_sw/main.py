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
import threading

URL = "http://192.168.116.207:81/stream"

record_flag = threading.Event()

def input_listener():
    """Toggle recording on each Enter press. Swap this for HTTP/BLE/etc later."""
    while True:
        input("Press Enter to start recording...")
        record_flag.set()
        input("Press Enter to stop recording...")
        record_flag.clear()

threading.Thread(target=input_listener, daemon=True).start() # daemon=true, means that the thread will be killed/stopped if tha main.py script reaches its end
                                                            #in this case, when camera_record dies for e.g. due to hitting q
                                                            # you can keep it running in the background by setting daemon=false (thread runs until it finishes on its own)


camera_record(URL, record_flag)