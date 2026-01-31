"""
PaddleOCR 文字识别模块

优先使用 OCR Server API，如果不可用则回退到本地模型。
"""
import os
import json
import base64
import httpx

OCR_SERVER_URL = os.environ.get("OCR_SERVER_URL", "http://127.0.0.1:8089")
_ocr = None
_use_api = None  # None=未检测, True=使用API, False=使用本地


def _check_server():
    """检查 OCR Server 是否可用"""
    global _use_api
    if _use_api is not None:
        return _use_api
    try:
        resp = httpx.get(f"{OCR_SERVER_URL}/health", timeout=1.0)
        _use_api = resp.status_code == 200
    except:
        _use_api = False
    return _use_api


def _get_local_ocr():
    """获取本地 OCR 实例"""
    global _ocr
    if _ocr is None:
        os.environ["PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK"] = "True"
        from paddleocr import PaddleOCR
        _ocr = PaddleOCR(
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=False,
            device="gpu",
        )
    return _ocr


def _recognize_local(img_path: str) -> list[dict]:
    """使用本地模型识别"""
    ocr = _get_local_ocr()
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
                    "center": (cx, cy),
                    "score": float(score),
                })
    return items


def _recognize_api(img_path: str) -> list[dict]:
    """使用 API 识别"""
    resp = httpx.post(
        f"{OCR_SERVER_URL}/ocr",
        json={"image": img_path, "is_path": True},
        timeout=30.0,
    )
    data = resp.json()
    if not data.get("ok"):
        raise RuntimeError(data.get("error", "OCR failed"))
    # 转换 center 为 tuple
    for item in data["items"]:
        item["center"] = tuple(item["center"])
    return data["items"]


def recognize(img_path: str) -> list[dict]:
    """
    识别图片中的文字，返回文字位置和内容。

    Returns:
        list of dict: [{"text": str, "box": [...], "center": (x,y), "score": float}, ...]
    """
    if _check_server():
        return _recognize_api(img_path)
    return _recognize_local(img_path)


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
    # 使用 API 时可以直接调用 /find 端点
    if _check_server():
        resp = httpx.post(
            f"{OCR_SERVER_URL}/find",
            json={
                "image": img_path,
                "is_path": True,
                "target": target,
                "exact": exact,
                "region": region,
                "near": near,
            },
            timeout=30.0,
        )
        data = resp.json()
        if not data.get("ok"):
            return None
        item = data["item"]
        item["center"] = tuple(item["center"])
        return item

    # 本地模式
    items = recognize(img_path)

    # 获取图片尺寸用于 region 计算
    if region and not img_size:
        try:
            from PIL import Image
            with Image.open(img_path) as img:
                img_size = img.size
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
        if exact:
            if item["text"] != target:
                continue
        else:
            if target.lower() not in item["text"].lower():
                continue

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
    parser.add_argument("-p", "--with-position", action="store_true", help="输出包含坐标信息")
    parser.add_argument("--local", action="store_true", help="强制使用本地模型")
    args = parser.parse_args()

    if args.local:
        _use_api = False

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
        elif args.with_position:
            for item in items:
                bbox = item["bbox"]
                print(f"({bbox[0]},{bbox[1]}) ({bbox[2]},{bbox[3]}) | {item['text']}")
        else:
            for item in items:
                print(item['text'])
