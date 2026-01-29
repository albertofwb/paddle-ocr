from paddleocr import PaddleOCR

# Paddleocr目前支持的多语言语种可以通过修改lang参数进行切换
# 例如`ch`, `en`, `fr`, `german`, `korean`, `japan`
ocr = PaddleOCR(lang="ch", use_doc_orientation_classify=False, use_doc_unwarping=False, use_textline_orientation=False)
img_path = 't1.jpg'
result = list(ocr.predict(img_path))

for res in result:
    if hasattr(res, 'keys'):
        boxes = res.get('rec_polys', res.get('dt_polys', []))
        txts = res.get('rec_texts', [])
        scores = res.get('rec_scores', [])

        for box, txt, score in zip(boxes, txts, scores):
            # box[0] 左上角, box[2] 右下角
            top_left = f"({int(box[0][0])},{int(box[0][1])})"
            bot_right = f"({int(box[2][0])},{int(box[2][1])})"
            print(f"位置: {top_left} {bot_right} | 文字: {txt} | 置信度: {score:.2f}")
