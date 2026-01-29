## Project Rules

1. Use `uv` to manage dependencies
   ```bash
   uv sync
   uv add <package>
   ```

2. Run with env var:
   ```bash
   PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True uv run python main.py
   ```

## CLI (for AI agents)

```bash
# 点击 (静默模式省token)
./click.sh "发布"              # 成功exit 0, 失败exit 1
./click.sh "发布" -v           # 显示输出

# OCR
./ocr.sh screenshot.png -t "登录" -j   # JSON输出
./ocr.sh --cdp -t "发布" -c -q         # CDP静默点击
```

## Output Format

| 模式 | 成功 | 失败 |
|------|------|------|
| 静默(-q) | 无输出 exit 0 | exit 1 |
| 默认 | `clicked:x,y` | `not_found:目标` |
| JSON(-j) | `{"ok":true,"clicked":[x,y]}` | `{"ok":false,"error":"not_found","texts":[...]}` |
