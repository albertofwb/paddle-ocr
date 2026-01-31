"""
OCR Server - FastAPI 服务，预加载模型提供高速 OCR API

启动: uv run uvicorn ocr_server:app --host 0.0.0.0 --port 8089
"""
import os
import base64
import tempfile
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"

from paddleocr import PaddleOCR

_ocr = None


def get_ocr():
    global _ocr
    if _ocr is None:
        _ocr = PaddleOCR(
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
            device="gpu",
        )
    return _ocr


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时预加载模型
    print("Loading OCR model...")
    get_ocr()
    print("OCR model loaded!")
    yield


app = FastAPI(title="OCR Server", lifespan=lifespan)


class OCRRequest(BaseModel):
    image: str  # base64 encoded image or file path
    is_path: bool = False


class FindTextRequest(BaseModel):
    image: str
    is_path: bool = False
    target: str
    exact: bool = False
    region: str | None = None
    near: str | None = None


def process_image(image: str, is_path: bool) -> str:
    """处理图片输入，返回文件路径"""
    if is_path:
        if not Path(image).exists():
            raise HTTPException(status_code=400, detail=f"File not found: {image}")
        return image
    else:
        # base64 解码并保存到临时文件
        img_data = base64.b64decode(image)
        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as f:
            f.write(img_data)
            return f.name


def recognize_image(img_path: str) -> list[dict]:
    """识别图片中的文字"""
    ocr = get_ocr()
    result = list(ocr.predict(img_path))

    items = []
    for res in result:
        if hasattr(res, "keys"):
            boxes = res.get("rec_polys", res.get("dt_polys", []))
            txts = res.get("rec_texts", [])
            scores = res.get("rec_scores", [])

            for box, txt, score in zip(boxes, txts, scores):
                int_box = [(int(p[0]), int(p[1])) for p in box]
                cx = sum(p[0] for p in int_box) // 4
                cy = sum(p[1] for p in int_box) // 4
                x1 = min(p[0] for p in int_box)
                y1 = min(p[1] for p in int_box)
                x2 = max(p[0] for p in int_box)
                y2 = max(p[1] for p in int_box)

                items.append({
                    "text": txt,
                    "box": int_box,
                    "bbox": [x1, y1, x2, y2],
                    "center": [cx, cy],
                    "score": float(score),
                })
    return items


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/ocr")
async def ocr(req: OCRRequest):
    """识别图片中的所有文字"""
    img_path = process_image(req.image, req.is_path)
    try:
        items = recognize_image(img_path)
        return {"ok": True, "items": items}
    finally:
        if not req.is_path:
            Path(img_path).unlink(missing_ok=True)


@app.post("/find")
async def find_text(req: FindTextRequest):
    """查找指定文字"""
    img_path = process_image(req.image, req.is_path)
    try:
        items = recognize_image(img_path)

        # 获取图片尺寸用于 region 计算
        img_size = None
        if req.region:
            from PIL import Image
            with Image.open(img_path) as img:
                img_size = img.size

        # 如果有 near 参数，先找到参考文字的位置
        near_center = None
        if req.near:
            for item in items:
                if req.near.lower() in item["text"].lower():
                    near_center = item["center"]
                    break

        # 过滤和匹配
        candidates = []
        for item in items:
            if req.exact:
                if item["text"] != req.target:
                    continue
            else:
                if req.target.lower() not in item["text"].lower():
                    continue

            if req.region and img_size:
                cx, cy = item["center"]
                w, h = img_size
                if req.region == "top" and cy > h * 0.4:
                    continue
                elif req.region == "bottom" and cy < h * 0.6:
                    continue
                elif req.region == "left" and cx > w * 0.4:
                    continue
                elif req.region == "right" and cx < w * 0.6:
                    continue
                elif req.region == "center":
                    if not (w * 0.3 < cx < w * 0.7 and h * 0.3 < cy < h * 0.7):
                        continue

            candidates.append(item)

        if not candidates:
            return {"ok": False, "error": "not_found", "texts": [i["text"] for i in items]}

        # 如果有 near 参数，返回最近的候选
        if near_center and len(candidates) > 1:
            def distance(item):
                cx, cy = item["center"]
                nx, ny = near_center
                return (cx - nx) ** 2 + (cy - ny) ** 2
            candidates.sort(key=distance)

        return {"ok": True, "item": candidates[0]}
    finally:
        if not req.is_path:
            Path(img_path).unlink(missing_ok=True)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8089)
