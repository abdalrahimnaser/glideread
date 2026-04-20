from paddleocr import PaddleOCR, PaddleOCRVL
pipeline = PaddleOCRVL()
output = pipeline.predict("stitched_result.png")
for res in output:
    res.print()
    res.save_to_json(save_path="output")
    res.save_to_markdown(save_path="output")