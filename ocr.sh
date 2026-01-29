#!/bin/bash
# OCR 浏览器自动化工具
# 用法:
#   ocr.sh image.png                    # OCR 本地图片
#   ocr.sh image.png -t "登录"          # 查找特定文字
#   ocr.sh --cdp                        # 截取当前浏览器
#   ocr.sh --cdp -t "发布" --click      # 查找并点击

script_path="$(cd "$(dirname "$0")" && pwd)"
cd "$script_path"
PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True uv run python main.py "$@"
