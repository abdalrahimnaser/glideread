
# Source - https://stackoverflow.com/a/45639406
# Posted by Elouarn Laine, modified by community. See post 'Timeline' for change history
# Retrieved 2026-02-28, License - CC BY-SA 3.0

import numpy as np
import cv2
import pytesseract
H_templ_ratio = 0.45
def prepare_for_ocr(img):
    # 1. Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # 2. Rescale (Upscaling 2x helps OCR detect smaller text)
    # Tesseract prefers characters that are at least 30 pixels tall
    gray = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)

    # 3. Bilateral Filter to smooth noise while keeping edges sharp
    # (9 = diameter, 75 = sigmaColor, 75 = sigmaSpace)
    denoised = cv2.bilateralFilter(gray, 9, 75, 75)

    # 4. Adaptive Thresholding
    # 31 is the block size (must be odd), 2 is the constant subtracted from the mean
    thresh = cv2.adaptiveThreshold(denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
                                  cv2.THRESH_BINARY, 31, 2)

    # 5. Optional: Sharpening
    kernel = np.array([[-1,-1,-1], [-1,9,-1], [-1,-1,-1]])
    sharpened = cv2.filter2D(thresh, -1, kernel)

    return sharpened


def genTemplate(img): 
    # we get the image's width and height
    h, w = img.shape[:2]
    # we compute the template's bounds
    x1 = int(float(w)*(1-H_templ_ratio))
    y1 = 0
    x2 = w
    y2 = h
    return(img[y1:y2,x1:x2]) # and crop the input image

def mat2Edges(img): # applies a Canny filter to get the edges
    edged = cv2.Canny(img, 100, 200)
    return(edged)

def addBlackMargins(img, top, bottom, left, right): # top, bottom, left, right: margins width in pixels
    h, w = img.shape[:2]
    result = np.zeros((h+top+bottom, w+left+right, 3), np.uint8)
    result[top:top+h,left:left+w] = img
    return(result)

# return the y_offset of the first image to stitch and the final image size needed
def calcFinalImgSize(imgs, loc):
    global V_templ_ratio, H_templ_ratio
    y_offset = 0
    max_margin_top = 0; max_margin_bottom = 0 # maximum margins that will be needed above and bellow the first image in order to stitch all the images into one mat
    current_margin_top = 0; current_margin_bottom = 0

    h_init, w_init = imgs[0].shape[:2]
    w_final = w_init
    
    for i in range(0,len(loc)):
        h, w = imgs[i].shape[:2]
        h2, w2 = imgs[i+1].shape[:2]
        # we compute the max top/bottom margins that will be needed (relatively to the first input image) in order to stitch all the images
        current_margin_top += loc[i][1] # here, we assume that the template top-left corner Y-coordinate is 0 (relatively to its original image)
        current_margin_bottom += (h2 - loc[i][1]) - h
        if(current_margin_top > max_margin_top): max_margin_top = current_margin_top
        if(current_margin_bottom > max_margin_bottom): max_margin_bottom = current_margin_bottom
        # we compute the width needed for the final result
        x_templ = int(float(w)*H_templ_ratio) # x-coordinate of the template relatively to its original image
        w_final += (w2 - x_templ - loc[i][0]) # width needed to stitch all the images into one mat

    h_final = h_init + max_margin_top + max_margin_bottom
    return (max_margin_top, h_final, w_final)

# match each input image with its following image (1->2, 2->3) 
def matchImages(imgs, templates_loc):
    for i in range(0,len(imgs)-1):
        template = genTemplate(imgs[i])
        template = mat2Edges(template)
        h_templ, w_templ = template.shape[:2]
        # Apply template Matching
        margin_top = margin_bottom = h_templ; margin_left = margin_right = 0
        img = addBlackMargins(imgs[i+1],margin_top, margin_bottom, margin_left, margin_right) # we need to enlarge the input image prior to call matchTemplate (template needs to be strictly smaller than the input image)
        img = mat2Edges(img)
        res = cv2.matchTemplate(img,template,cv2.TM_CCOEFF) # matching function
        _, _, _, templ_pos = cv2.minMaxLoc(res) # minMaxLoc gets the best match position
        # as we added margins to the input image we need to subtract the margins width to get the template position relatively to the initial input image (without the black margins)
        rectified_templ_pos = (templ_pos[0]-margin_left, templ_pos[1]-margin_top) 
        templates_loc.append(rectified_templ_pos)
        print("max_loc", rectified_templ_pos)

def stitchImages(imgs, templates_loc):
    y_offset, h_final, w_final = calcFinalImgSize(imgs, templates_loc) # we calculate the "surface" needed to stitch all the images into one mat (and y_offset, the Y offset of the first image to be stitched) 
    result = np.zeros((h_final, w_final, 3), np.uint8)

    #initial stitch
    h_init, w_init = imgs[0].shape[:2]
    result[y_offset:y_offset+h_init, 0:w_init] = imgs[0]
    origin = (y_offset, 0) # top-left corner of the last stitched image (y,x)
    # stitching loop
    for j in range(0,len(templates_loc)):
        h, w = imgs[j].shape[:2]
        h2, w2 = imgs[j+1].shape[:2]
        # we compute the coordinates where to stitch imgs[j+1]
        y1 = origin[0] - templates_loc[j][1]
        y2 = origin[0] - templates_loc[j][1] + h2
        x_templ = int(float(w)*(1-H_templ_ratio)) # x-coordinate of the template relatively to its original image's right side
        x1 = origin[1] + x_templ - templates_loc[j][0]
        x2 = origin[1] + x_templ - templates_loc[j][0] + w2
        result[y1:y2, x1:x2] = imgs[j+1] # we copy the input image into the result mat
        origin = (y1,x1) # we update the origin point with the last stitched image

    return(result)

def excute():
    frame_skip = 20
    count = 0
    cap = cv2.VideoCapture('roi_capture.mp4')
    final_output = []


    print("Starting smart scan...")

    while True:
        ret, frame = cap.read()
        if not ret: break
        
        if count % frame_skip == 0:
            final_output.append(frame)

        #print(pytesseract.image_to_string(frame, config=r'--oem 3 --psm 6'))

        count += 1

     # H_templ_ratio: horizontal ratio of the input that we will keep to create a template
    templates_loc = [] # templates location

    matchImages(final_output, templates_loc)
    
    result = stitchImages(final_output, templates_loc)

    cv2.imshow("result", result)

    print(pytesseract.image_to_string(result, config=r'--oem 3 --psm 6'))

    while True:
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

excute()


# import cv2
# import numpy as np
# import pytesseract


# def stitch_panorama(video_path, frame_drop_factor=5, max_frames=None, blur_threshold=100.0):
    
#     cap = cv2.VideoCapture(video_path)
#     frames = []
#     frame_count = 0
    
#     while True:
#         ret, frame = cap.read()
#         if not ret:
#             break
	
#         #_, frame = cv2.threshold(frame, 127, 255, cv2.THRESH_BINARY)

#         if frame_count % frame_drop_factor == 0:
#             frames.append(frame)

#             if max_frames and len(frames) >= max_frames:
#                 break
        
#         # print(pytesseract.image_to_string(frame, config=r'--oem 3 --psm 6'))
#         frame_count += 1
    
#     cap.release()
    
#     if len(frames) < 2:
#         print("Not enough sharp frames found to stitch! Try lowering the blur_threshold.")
#         return
    
#     stitcher = cv2.Stitcher.create(cv2.Stitcher_SCANS)
#     print(len(frames))

#     status, result = stitcher.stitch(frames)

#     if status != cv2.Stitcher_OK:
#         print(f"Stitching failed with status code {status}")
#         return

#     # while len(results)>1:
#     #     print(f"Stitching {len(results)} frames...")
#     #     temp = []
#     #     for i in range(0, len(results)-1, 2):
#     #         status, result = stitcher.stitch([results[i], results[i+1]])
#     #         if status == cv2.Stitcher_OK:
#     #             temp.append(result)
#     #         else:
#     #             print(f"Stitching failed for frames {i} and {i+1} with status code {status}")
#     #     results = temp
    
#     cv2.imshow('Panorama', result)
    
#     # Configure Tesseract
#     custom_config = r'--oem 3 --psm 6'
#     text = pytesseract.image_to_string(result, config=custom_config)
    
#     print("--- Extracted Text ---")
#     print(text)
    
#     cv2.imwrite('panorama_result.jpg', result)
#     cv2.waitKey(0)
#     cv2.destroyAllWindows()


# # Example usage
# video_path = "roi_capture.mp4"

# # NOTE: I changed frame_drop_factor to 5. Since we are rejecting blurry frames, 
# # we need to look at more frames overall to find enough good ones.
# stitch_panorama(video_path, frame_drop_factor=1, max_frames=None, blur_threshold=65.0)