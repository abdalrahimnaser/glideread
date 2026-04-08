import cv2

def nothing(x):
    pass

# Load the image
img = cv2.imread('snap_1.png', cv2.IMREAD_GRAYSCALE)

# Create a window
cv2.namedWindow('Tuner')

# Create trackbars for adjustment
# Block size must be odd and > 1. We'll handle the 'odd' part in the loop.
cv2.createTrackbar('Block Size', 'Tuner', 11, 51, nothing)
cv2.createTrackbar('Constant C', 'Tuner', 2, 20, nothing)

print("Adjust the sliders. Press 'q' to quit and save the current values.")

while True:
    # Get current positions of trackbars
    bs = cv2.getTrackbarPos('Block Size', 'Tuner')
    c = cv2.getTrackbarPos('Constant C', 'Tuner')

    # Block size MUST be odd and at least 3
    if bs % 2 == 0:
        bs += 1
    if bs < 3:
        bs = 3

    # Apply adaptive thresholding
    # Using Gaussian version for smoother results on gradients
    # descent values were bs = 17 and c=7
    thresh = cv2.adaptiveThreshold(img, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                   cv2.THRESH_BINARY, bs, c)

    # Show the result
    cv2.imshow('Tuner', thresh)

    # Exit on 'q'
    if cv2.waitKey(1) & 0xFF == ord('q'):
        print(f"Final Parameters: Block Size = {bs}, Constant C = {c}")
        cv2.imwrite('optimized_text.jpg', thresh)
        break

cv2.destroyAllWindows()


