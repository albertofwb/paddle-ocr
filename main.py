import argparse

from paddleocr import PaddleOCR

parser = argparse.ArgumentParser(description="PaddleOCR 文字识别工具")
parser.add_argument("image", nargs="?", default="t1.jpg", help="要识别的图片路径")
args = parser.parse_args()

ocr = PaddleOCR(
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,
    use_textline_orientation=False,
    enable_mkldnn=False,
)
img_path = args.image
result = list(ocr.predict(img_path))

for res in result:
    if hasattr(res, "keys"):
        boxes = res.get("rec_polys", res.get("dt_polys", []))
        txts = res.get("rec_texts", [])
        scores = res.get("rec_scores", [])

        for box, txt, score in zip(boxes, txts, scores):
            # box[0] 左上角, box[2] 右下角
            top_left = f"({int(box[0][0])},{int(box[0][1])})"
            bot_right = f"({int(box[2][0])},{int(box[2][1])})"
            print(f"{top_left} {bot_right} | {txt}")
