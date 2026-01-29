#!/usr/bin/env python3
"""
OCR 浏览器自动化工具

支持：
- 连接已运行的浏览器 (CDP)
- 截图 + OCR + 点击
- 本地图片 OCR
"""
import argparse
import asyncio
import json
import tempfile
import sys
from pathlib import Path

from playwright.async_api import async_playwright

from ocr import recognize, find_text, find_text_item

# Clawdbot 默认 CDP 端口
DEFAULT_CDP_URL = "http://127.0.0.1:18800"


async def connect_browser(cdp_url: str = DEFAULT_CDP_URL):
    """连接到已运行的浏览器"""
    p = await async_playwright().start()
    browser = await p.chromium.connect_over_cdp(cdp_url)
    context = browser.contexts[0]
    page = context.pages[0] if context.pages else await context.new_page()
    return p, browser, page


async def screenshot_ocr(
    cdp_url: str = DEFAULT_CDP_URL,
    target: str = None,
    exact: bool = False,
    click: bool = False,
    output_json: bool = False,
):
    """
    截取当前页面并 OCR 识别。

    Args:
        cdp_url: CDP 连接地址
        target: 查找特定文字
        exact: 精确匹配
        click: 找到后点击
        output_json: JSON 输出
    """
    p, browser, page = await connect_browser(cdp_url)
    
    try:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            screenshot_path = f.name

        # viewport 截图
        await page.screenshot(path=screenshot_path, full_page=False)

        if target:
            item = find_text_item(screenshot_path, target, exact=exact)
            if item:
                if output_json:
                    print(json.dumps(item, ensure_ascii=False))
                else:
                    print(f"找到 \"{item['text']}\" 坐标: {item['center']}")
                
                if click:
                    cx, cy = item["center"]
                    await page.mouse.click(cx, cy)
                    print(f"已点击 ({cx}, {cy})")
            else:
                print(f"未找到 \"{target}\"", file=sys.stderr)
                sys.exit(1)
        else:
            items = recognize(screenshot_path)
            if output_json:
                print(json.dumps(items, ensure_ascii=False, indent=2))
            else:
                for item in items:
                    bbox = item["bbox"]
                    print(f"({bbox[0]},{bbox[1]}) ({bbox[2]},{bbox[3]}) | {item['text']}")

        Path(screenshot_path).unlink()
    finally:
        await p.stop()


async def ocr_and_click(
    cdp_url: str,
    target: str,
    exact: bool = False,
    wait_ms: int = 0,
):
    """
    OCR 查找文字并点击。简化版本，专为自动化设计。
    
    Returns:
        成功返回点击坐标，失败返回 None
    """
    p, browser, page = await connect_browser(cdp_url)
    
    try:
        if wait_ms > 0:
            await asyncio.sleep(wait_ms / 1000)
            
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            screenshot_path = f.name

        await page.screenshot(path=screenshot_path, full_page=False)
        item = find_text_item(screenshot_path, target, exact=exact)
        Path(screenshot_path).unlink()
        
        if item:
            cx, cy = item["center"]
            await page.mouse.click(cx, cy)
            return (cx, cy)
        return None
    finally:
        await p.stop()


async def screenshot_and_ocr_url(url: str, target: str = None, output_json: bool = False):
    """
    打开 URL 截图并 OCR（启动新浏览器）
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(viewport={"width": 1280, "height": 720})
        await page.goto(url)
        await page.wait_for_load_state("networkidle")

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            screenshot_path = f.name

        await page.screenshot(path=screenshot_path, full_page=False)

        if target:
            item = find_text_item(screenshot_path, target)
            if item:
                if output_json:
                    print(json.dumps(item, ensure_ascii=False))
                else:
                    print(f"找到 \"{item['text']}\" 坐标: {item['center']}")
            else:
                print(f"未找到 \"{target}\"", file=sys.stderr)
        else:
            items = recognize(screenshot_path)
            if output_json:
                print(json.dumps(items, ensure_ascii=False, indent=2))
            else:
                for item in items:
                    bbox = item["bbox"]
                    print(f"({bbox[0]},{bbox[1]}) ({bbox[2]},{bbox[3]}) | {item['text']}")

        Path(screenshot_path).unlink()
        await browser.close()


async def ocr_local_image(img_path: str, target: str = None, exact: bool = False, output_json: bool = False):
    """
    对本地图片进行 OCR
    """
    if target:
        item = find_text_item(img_path, target, exact=exact)
        if item:
            if output_json:
                print(json.dumps(item, ensure_ascii=False))
            else:
                print(f"找到 \"{item['text']}\" 坐标: {item['center']}")
        else:
            print(f"未找到 \"{target}\"", file=sys.stderr)
            sys.exit(1)
    else:
        items = recognize(img_path)
        if output_json:
            print(json.dumps(items, ensure_ascii=False, indent=2))
        else:
            for item in items:
                bbox = item["bbox"]
                print(f"({bbox[0]},{bbox[1]}) ({bbox[2]},{bbox[3]}) | {item['text']}")


def main():
    parser = argparse.ArgumentParser(
        description="OCR 浏览器自动化工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 对本地图片 OCR
  %(prog)s screenshot.png
  
  # 查找特定文字
  %(prog)s screenshot.png -t "登录"
  
  # 截取当前浏览器页面并 OCR (连接 Clawdbot)
  %(prog)s --cdp
  
  # 查找并点击
  %(prog)s --cdp -t "发布" --click
  
  # 精确匹配 (避免 "Post" 匹配到 "posts")
  %(prog)s --cdp -t "Post" --exact --click
  
  # 打开 URL 并 OCR
  %(prog)s https://example.com
        """
    )
    parser.add_argument("source", nargs="?", help="图片路径或 URL")
    parser.add_argument("-t", "--target", help="查找特定文字")
    parser.add_argument("-e", "--exact", action="store_true", help="精确匹配")
    parser.add_argument("-c", "--click", action="store_true", help="找到后点击 (需要 --cdp)")
    parser.add_argument("-j", "--json", action="store_true", help="JSON 输出")
    parser.add_argument("--cdp", nargs="?", const=DEFAULT_CDP_URL, metavar="URL",
                       help=f"连接已运行的浏览器 (默认: {DEFAULT_CDP_URL})")
    args = parser.parse_args()

    # CDP 模式：截取当前页面
    if args.cdp:
        asyncio.run(screenshot_ocr(
            cdp_url=args.cdp,
            target=args.target,
            exact=args.exact,
            click=args.click,
            output_json=args.json,
        ))
    elif args.source:
        source = args.source
        if source.startswith("http://") or source.startswith("https://"):
            asyncio.run(screenshot_and_ocr_url(source, args.target, args.json))
        else:
            asyncio.run(ocr_local_image(source, args.target, args.exact, args.json))
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
