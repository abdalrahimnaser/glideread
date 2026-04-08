import cv2
import numpy as np

def deblur_text(image_path):
    # 1. Load the image in grayscale
    img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    
    # 2. Rescale (Optional but helpful for small text)
    # Increasing size can sometimes help the filters find edges better
    img = cv2.resize(img, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)

    # 3. Apply Unsharp Masking
    # This enhances high-frequency details (edges of letters)
    gaussian_3 = cv2.GaussianBlur(img, (0, 0), 3)
    unsharp_image = cv2.addWeighted(img, 1.5, gaussian_3, -0.5, 0)

    # 4. Use a Sharpening Kernel
    kernel = np.array([[-1,-1,-1], 
                       [-1, 9,-1], 
                       [-1,-1,-1]])
    sharpened = cv2.filter2D(unsharp_image, -1, kernel)

    # 5. Adaptive Thresholding (The "Secret Sauce" for text)
    # This converts it to high-contrast black and white
    final_bin = cv2.adaptiveThreshold(sharpened, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                      cv2.THRESH_BINARY, 11, 2)

    return final_bin

# Usage
result = deblur_text('blurry_image.png')
cv2.imshow('fixed_text', result)
cv2.waitKey(0)