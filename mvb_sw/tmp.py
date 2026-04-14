import pytesseract

text = pytesseract.image_to_string("t.png")
print(text)