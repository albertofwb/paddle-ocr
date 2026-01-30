"""
PaddleOCR 文字识别模块

提供单例 OCR 实例，避免重复加载模型。
"""
import json
from paddleocr import PaddleOCR

_ocr = None


def get_ocr():
    global _ocr
    if _ocr is None:
        _ocr = PaddleOCR(
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
            enable_mkldnn=False,
        )
    return _ocr


def recognize(img_path: str) -> list[dict]:
    """
    识别图片中的文字，返回文字位置和内容。

    Returns:
        list of dict: [{"text": str, "box": [...], "center": (x,y), "score": float}, ...]
    """
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
                # 计算中心点和边界框
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
                    "center": (cx, cy),
                    "score": float(score),
                })
    return items


def find_text(
    img_path: str, 
    target: str, 
    exact: bool = False,
    all_matches: bool = False
) -> tuple[int, int] | list[tuple[int, int]] | None:
    """
    查找指定文字的中心点坐标。

    Args:
        img_path: 图片路径
        target: 要查找的文字
        exact: True 时精确匹配，False 时包含匹配
        all_matches: True 时返回所有匹配，False 时返回第一个

    Returns:
        (x, y) 中心坐标，或坐标列表，未找到返回 None
    """
    items = recognize(img_path)
    matches = []
    
    for item in items:
        if exact:
            if item["text"] == target:
                matches.append(item["center"])
        else:
            if target.lower() in item["text"].lower():
                matches.append(item["center"])
    
    if not matches:
        return None
    
    if all_matches:
        return matches
    return matches[0]


def find_text_item(
    img_path: str, 
    target: str, 
    exact: bool = False,
    region: str = None,
    near: str = None,
    img_size: tuple[int, int] = None,
) -> dict | None:
    """
    查找指定文字，返回完整信息。

    Args:
        img_path: 图片路径
        target: 要查找的文字
        exact: True 时精确匹配，False 时包含匹配
        region: 位置过滤 - "top", "bottom", "left", "right", "center"
        near: 上下文匹配 - 查找靠近此文字的目标
        img_size: 图片尺寸 (width, height)，用于 region 计算

    Returns:
        dict with text, box, bbox, center, score，未找到返回 None
    """
    items = recognize(img_path)
    
    # 获取图片尺寸用于 region 计算
    if region and not img_size:
        try:
            from PIL import Image
            with Image.open(img_path) as img:
                img_size = img.size  # (width, height)
        except:
            pass
    
    # 如果有 near 参数，先找到参考文字的位置
    near_center = None
    if near:
        for item in items:
            if near.lower() in item["text"].lower():
                near_center = item["center"]
                break
    
    # 过滤和匹配
    candidates = []
    for item in items:
        # 文字匹配
        if exact:
            if item["text"] != target:
                continue
        else:
            if target.lower() not in item["text"].lower():
                continue
        
        # 位置过滤
        if region and img_size:
            cx, cy = item["center"]
            w, h = img_size
            
            if region == "top" and cy > h * 0.4:
                continue
            elif region == "bottom" and cy < h * 0.6:
                continue
            elif region == "left" and cx > w * 0.4:
                continue
            elif region == "right" and cx < w * 0.6:
                continue
            elif region == "center":
                if not (w * 0.3 < cx < w * 0.7 and h * 0.3 < cy < h * 0.7):
                    continue
        
        candidates.append(item)
    
    if not candidates:
        return None
    
    # 如果有 near 参数，返回最近的候选
    if near_center and len(candidates) > 1:
        def distance(item):
            cx, cy = item["center"]
            nx, ny = near_center
            return (cx - nx) ** 2 + (cy - ny) ** 2
        candidates.sort(key=distance)
    
    return candidates[0]


if __name__ == "__main__":
    import argparse
    import sys
    
    parser = argparse.ArgumentParser(description="PaddleOCR 文字识别工具")
    parser.add_argument("image", nargs="?", default="t1.jpg", help="要识别的图片路径")
    parser.add_argument("-t", "--target", help="查找特定文字")
    parser.add_argument("-e", "--exact", action="store_true", help="精确匹配")
    parser.add_argument("-j", "--json", action="store_true", help="JSON 输出")
    parser.add_argument("-T", "--text-only", action="store_true", help="仅输出文字，不含坐标")
    args = parser.parse_args()

    items = recognize(args.image)
    
    if args.target:
        item = find_text_item(args.image, args.target, exact=args.exact)
        if item:
            if args.json:
                print(json.dumps(item, ensure_ascii=False))
            else:
                print(f"找到 \"{item['text']}\" 点击坐标: {item['center']}")
        else:
            print(f"未找到 \"{args.target}\"", file=sys.stderr)
            sys.exit(1)
    else:
        if args.json:
            print(json.dumps(items, ensure_ascii=False, indent=2))
        elif args.text_only:
            for item in items:
                print(item['text'])
        else:
            for item in items:
                bbox = item["bbox"]
                print(f"({bbox[0]},{bbox[1]}) ({bbox[2]},{bbox[3]}) | {item['text']}")
