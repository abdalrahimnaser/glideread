import pytesseract
import cv2
from difflib import SequenceMatcher

def filter_and_stitch(all_frames_text):
    final_sentence = []
    for frame_text in all_frames_text:
        words = frame_text.split()
        print(words)
        for word in words:

            clean_word = "".join(c for c in word if c.isalnum()) # regect anything not a letter or number

            if len(clean_word) < 2: continue
            
            # If the word is already at the end of our sentence, skip it (Deduplication)
            if not final_sentence:
                final_sentence.append(clean_word)
            else:
                # Compare with the last word added
                similarity = SequenceMatcher(None, final_sentence[-1].lower(), clean_word.lower()).ratio()
                if similarity < 0.6:
                    final_sentence.append(clean_word)
                    
    return " ".join(final_sentence)


captured_texts = []
image_paths = [f"snap_{i}.png" for i in range(1, 14)]

for path in image_paths:
    img = cv2.imread(path)
    # Get raw text
    raw_text = pytesseract.image_to_string(img, config=r'--oem 3 --psm 6')
    captured_texts.append(raw_text)

result = filter_and_stitch(captured_texts)
print(f"Final Stitched Text: {result}")




