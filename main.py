#!/usr/bin/env python3
"""
OCR 浏览器自动化工具

支持：
- 连接已运行的浏览器 (CDP)
- 截图 + OCR + 点击
- 本地图片 OCR
- 出错时自动保存截图
"""
import argparse
import asyncio
import json
import tempfile
import sys
import shutil
from datetime import datetime
from pathlib import Path

from playwright.async_api import async_playwright

from ocr import recognize, find_text, find_text_item

# Clawdbot 默认 CDP 端口
DEFAULT_CDP_URL = "http://127.0.0.1:18800"

# 错误截图保存目录
ERROR_SCREENSHOT_DIR = Path("/tmp/ocr-debug")


def save_error_screenshot(screenshot_path: str, reason: str) -> str:
    """保存错误截图到调试目录"""
    ERROR_SCREENSHOT_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_reason = reason.replace(" ", "_").replace("/", "-")[:30]
    dest = ERROR_SCREENSHOT_DIR / f"{timestamp}_{safe_reason}.png"
    shutil.copy(screenshot_path, dest)
    print(f"📸 截图已保存: {dest}", file=sys.stderr)
    return str(dest)


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
    save_screenshot: str = None,
    wait_after_click: float = 3,
    expect_text: str = None,
    expect_gone: str = None,
):
    """
    截取当前页面并 OCR 识别。

    Args:
        cdp_url: CDP 连接地址
        target: 查找特定文字
        exact: 精确匹配
        click: 找到后点击
        output_json: JSON 输出
        save_screenshot: 保存截图到指定路径 (None=不保存)
    """
    p, browser, page = await connect_browser(cdp_url)
    screenshot_path = None
    error_occurred = False
    
    try:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            screenshot_path = f.name

        # viewport 截图
        await page.screenshot(path=screenshot_path, full_page=False)
        
        # 如果指定了保存路径，复制一份
        if save_screenshot:
            shutil.copy(screenshot_path, save_screenshot)
            print(f"📸 截图已保存: {save_screenshot}", file=sys.stderr)

        if target:
            item = find_text_item(screenshot_path, target, exact=exact)
            if item:
                if output_json:
                    print(json.dumps(item, ensure_ascii=False))
                else:
                    print(f"找到 \"{item['text']}\" 坐标: {item['center']}")
                
                if click:
                    # 获取 devicePixelRatio 校正坐标
                    dpr = await page.evaluate("window.devicePixelRatio")
                    cx, cy = item["center"]
                    actual_x, actual_y = int(cx / dpr), int(cy / dpr)
                    await page.mouse.click(actual_x, actual_y)
                    print(f"已点击 ({actual_x}, {actual_y}) [DPR={dpr}]")
                    
                    if wait_after_click > 0:
                        await asyncio.sleep(wait_after_click)
                        
                        # 点击后验证：再次截图 + OCR
                        await page.screenshot(path=screenshot_path, full_page=False)
                        new_items = recognize(screenshot_path)
                        new_texts_str = " ".join([i["text"] for i in new_items])
                        new_texts_list = [i["text"] for i in new_items[:15]]
                        
                        print(f"📄 页面文字: {new_texts_list}")
                        
                        # 验证期望出现的文字
                        if expect_text:
                            if expect_text.lower() in new_texts_str.lower():
                                print(f"✅ 验证成功: 找到 \"{expect_text}\"")
                            else:
                                print(f"❌ 验证失败: 未找到 \"{expect_text}\"")
                                save_error_screenshot(screenshot_path, f"expect_failed_{expect_text}")
                                sys.exit(1)
                        
                        # 验证期望消失的文字
                        if expect_gone:
                            if expect_gone.lower() not in new_texts_str.lower():
                                print(f"✅ 验证成功: \"{expect_gone}\" 已消失")
                            else:
                                print(f"❌ 验证失败: \"{expect_gone}\" 仍在页面上")
                                save_error_screenshot(screenshot_path, f"still_exists_{expect_gone}")
                                sys.exit(1)
                        
                        # 默认检查目标文字是否消失
                        if not expect_text and not expect_gone:
                            if target.lower() in new_texts_str.lower():
                                print(f"⚠️ 目标文字仍在页面上")
                            else:
                                print(f"✅ 目标文字已消失")
            else:
                error_occurred = True
                # 保存错误截图
                saved = save_error_screenshot(screenshot_path, f"not_found_{target}")
                # 输出所有识别到的文字帮助调试
                items = recognize(screenshot_path)
                texts = [i["text"] for i in items[:20]]
                print(f"未找到 \"{target}\"", file=sys.stderr)
                print(f"页面文字: {texts}", file=sys.stderr)
                sys.exit(1)
        else:
            items = recognize(screenshot_path)
            if output_json:
                print(json.dumps(items, ensure_ascii=False, indent=2))
            else:
                for item in items:
                    bbox = item["bbox"]
                    print(f"({bbox[0]},{bbox[1]}) ({bbox[2]},{bbox[3]}) | {item['text']}")

    except Exception as e:
        error_occurred = True
        if screenshot_path and Path(screenshot_path).exists():
            save_error_screenshot(screenshot_path, f"error_{type(e).__name__}")
        raise
    finally:
        if screenshot_path and Path(screenshot_path).exists() and not error_occurred:
            Path(screenshot_path).unlink()
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
    screenshot_path = None
    
    try:
        if wait_ms > 0:
            await asyncio.sleep(wait_ms / 1000)
            
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            screenshot_path = f.name

        await page.screenshot(path=screenshot_path, full_page=False)
        item = find_text_item(screenshot_path, target, exact=exact)
        
        if item:
            # 获取 devicePixelRatio 校正坐标
            dpr = await page.evaluate("window.devicePixelRatio")
            cx, cy = item["center"]
            actual_x, actual_y = int(cx / dpr), int(cy / dpr)
            await page.mouse.click(actual_x, actual_y)
            Path(screenshot_path).unlink()
            return (actual_x, actual_y)
        else:
            # 保存错误截图
            save_error_screenshot(screenshot_path, f"click_failed_{target}")
            return None
    except Exception as e:
        if screenshot_path and Path(screenshot_path).exists():
            save_error_screenshot(screenshot_path, f"error_{type(e).__name__}")
        raise
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
  
  # 查找并点击 (自动 DPR 校正)
  %(prog)s --cdp -t "发布" --click
  
  # 精确匹配 (避免 "Post" 匹配到 "posts")
  %(prog)s --cdp -t "Post" --exact --click
  
  # 保存截图用于调试
  %(prog)s --cdp -t "登录" --save /tmp/debug.png
  
  # 打开 URL 并 OCR
  %(prog)s https://example.com

验证模式:
  # 点击后验证期望文字出现
  %(prog)s --cdp -t "Create" --click --expect "Issue created"
  
  # 点击后验证目标消失
  %(prog)s --cdp -t "Submit" --click --expect-gone "Submit"

错误处理:
  - 找不到目标文字时，自动保存截图到 /tmp/ocr-debug/
  - 验证失败时，自动保存截图
  - 截图文件名包含时间戳和错误原因
  - 同时输出页面上识别到的所有文字帮助调试
        """
    )
    parser.add_argument("source", nargs="?", help="图片路径或 URL")
    parser.add_argument("-t", "--target", help="查找特定文字")
    parser.add_argument("-e", "--exact", action="store_true", help="精确匹配")
    parser.add_argument("-c", "--click", action="store_true", help="找到后点击 (需要 --cdp)")
    parser.add_argument("-j", "--json", action="store_true", help="JSON 输出")
    parser.add_argument("-s", "--save", metavar="PATH", help="保存截图到指定路径")
    parser.add_argument("-w", "--wait", type=float, default=3, metavar="SEC",
                       help="点击后等待秒数 (默认: 3)")
    parser.add_argument("--expect", metavar="TEXT",
                       help="期望点击后出现的文字 (验证成功)")
    parser.add_argument("--expect-gone", metavar="TEXT",
                       help="期望点击后消失的文字 (验证成功)")
    parser.add_argument("--cdp", nargs="?", const=DEFAULT_CDP_URL, metavar="URL",
                       help=f"连接已运行的浏览器 (默认: {DEFAULT_CDP_URL})")
    parser.add_argument("--debug-dir", default="/tmp/ocr-debug",
                       help="错误截图保存目录 (默认: /tmp/ocr-debug)")
    args = parser.parse_args()

    # 设置错误截图目录
    global ERROR_SCREENSHOT_DIR
    ERROR_SCREENSHOT_DIR = Path(args.debug_dir)
    
    # CDP 模式：截取当前页面
    if args.cdp:
        asyncio.run(screenshot_ocr(
            cdp_url=args.cdp,
            target=args.target,
            exact=args.exact,
            click=args.click,
            output_json=args.json,
            save_screenshot=args.save,
            wait_after_click=args.wait,
            expect_text=args.expect,
            expect_gone=args.expect_gone,
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
