#!/bin/bash

script_path="$(cd "$(dirname "$0")" && pwd)"
cd "$script_path"
PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True uv run python main.py "$@"
