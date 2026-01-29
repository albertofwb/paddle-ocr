#!/bin/bash
# 快捷点击: click.sh "文字" [--exact] [-v]
# 默认静默模式，-v 显示输出

script_path="$(cd "$(dirname "$0")" && pwd)"
cd "$script_path"

[ -z "$1" ] && { echo "用法: click.sh <文字> [--exact] [-v]"; exit 1; }

# 检查是否有 -v 参数
quiet="-q"
args=()
for arg in "$@"; do
    [ "$arg" = "-v" ] && quiet="" || args+=("$arg")
done

PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True uv run python main.py --cdp -t "${args[@]}" --click $quiet
