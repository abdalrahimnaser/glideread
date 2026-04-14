# Source - https://stackoverflow.com/a/45639406
# Posted by Elouarn Laine, modified by community. See post 'Timeline' for change history
# Retrieved 2026-03-01, License - CC BY-SA 3.0

import numpy as np
import cv2
import pytesseract


H_templ_ratio_ = None

def genTemplate(img): 
    global H_templ_ratio_
    # we get the image's width and height
    h, w = img.shape[:2]
    # we compute the template's bounds
    x1 = int(float(w)*(1-H_templ_ratio_))
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
    global V_templ_ratio, H_templ_ratio_
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
        x_templ = int(float(w)*H_templ_ratio_) # x-coordinate of the template relatively to its original image
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
        x_templ = int(float(w)*(1-H_templ_ratio_)) # x-coordinate of the template relatively to its original image's right side
        x1 = origin[1] + x_templ - templates_loc[j][0]
        x2 = origin[1] + x_templ - templates_loc[j][0] + w2
        result[y1:y2, x1:x2] = imgs[j+1] # we copy the input image into the result mat
        origin = (y1,x1) # we update the origin point with the last stitched image

    return(result)


def stitch_video_and_ocr(video_path, frame_skip=1, H_templ_ratio=0.65):
    global H_templ_ratio_
    H_templ_ratio_ = H_templ_ratio
    images = []
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise FileNotFoundError(f'OpenCV: Couldn\'t read video stream from file "{video_path}"')
    count = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if count % frame_skip == 0:
            # Recommendation for MVB: Books often have shadows from the binding. 
            # Before thresholding, apply a Dilation/Erosion or a Median Blur to remove noise. 
            # Also, Pytesseract works significantly better if the text is perfectly horizontal. 
            # Since your stitching might result in a slight "wave," you might want to look into 
            # deskewing libraries later.
            # consult a comouter vision expert to improve this bit for you if u needed more accuracy


            # essential filtering ... would yield better results if w/ flashlight
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            img = cv2.adaptiveThreshold(frame, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 27, 3)
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)  # Convert to 3-channel image
            images.append(img)

        count += 1
    
    cap.release()
    if not images:
        raise ValueError(f"No frames decoded from video: {video_path}")
    
    templates_loc = [] # templates location

    matchImages(images, templates_loc)
    
    result = stitchImages(images, templates_loc)
    text = pytesseract.image_to_string(result)
    # cv2.imshow("result", result)

    return text, result