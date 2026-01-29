#!/bin/bash
# 快捷点击脚本：OCR 查找文字并点击
# 用法: click.sh "发布"
#       click.sh "Post" --exact

script_path="$(cd "$(dirname "$0")" && pwd)"
cd "$script_path"

if [ -z "$1" ]; then
    echo "用法: click.sh <文字> [--exact]"
    exit 1
fi

PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True uv run python main.py --cdp -t "$@" --click
