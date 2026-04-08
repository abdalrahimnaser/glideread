from PIL import Image
import pytesseract
import cv2


img = cv2.imread("./20260301200906.jpg")
text = pytesseract.image_to_string(img)

print(text)


image_paths = [f"snap_{i}.png" for i in range(1, 14)]
for path in image_paths:
    img = cv2.imread(path)
    if img is None:
        print(f"Error: Could not load {path}")
        exit(1)
    text = pytesseract.image_to_string(img, config=r'--oem 3 --psm 6')
    print(text)