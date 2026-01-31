# Paddle OCR 浏览器自动化

用 PaddleOCR + Playwright 实现基于视觉的浏览器自动化。

## 为什么？

- **省 Token**: DOM snapshot 动辄上万 tokens，OCR 输出只有几十行
- **不依赖 DOM**: 网页结构变化不影响，只要文字还在就能找到
- **本地运行**: OCR 完全本地，0 API 消耗

## 安装

```bash
uv sync  # 需要 Python 3.10
```

## 快速使用

```bash
./click.sh "发布"              # 静默点击 (省token)
./click.sh "发布" -v           # 显示输出
./click.sh "Post" --exact      # 精确匹配
```

## CLI

```bash
# 本地图片
./ocr.sh screenshot.png
./ocr.sh screenshot.png -t "登录"

# 浏览器 (CDP)
./ocr.sh --cdp
./ocr.sh --cdp -t "发布" --click
./ocr.sh --cdp -t "发布" -c -q    # 静默模式
./ocr.sh --cdp -t "发布" -c -j    # JSON输出

# 多个相同文字 - 位置过滤
./ocr.sh --cdp -t "发布" -c --region bottom   # 底部区域
./ocr.sh --cdp -t "确定" -c --region right    # 右侧区域

# 多个相同文字 - 上下文匹配
./ocr.sh --cdp -t "发布" -c --near "预览"     # 找"预览"旁边的"发布"
```

## 输出格式

| 模式 | 成功 | 失败 |
|------|------|------|
| 默认 | `clicked:500,300` | `not_found:目标` |
| JSON | `{"ok":true,"clicked":[500,300]}` | `{"ok":false,"error":"not_found","texts":[...]}` |
| 静默(-q) | 无输出 (exit 0) | 错误信息 (exit 1) |

## Python API

```python
from ocr import recognize, find_text_item

items = recognize("screenshot.png")
item = find_text_item("screenshot.png", "登录", exact=True)
```

## OCR Server

预加载模型的 HTTP 服务，避免每次调用都加载模型（~3s → ~0.6s）。

```bash
sudo systemctl start ocr-server
sudo systemctl status ocr-server
```

> API 文档见 `API.md`（本地文件，不提交 git）

## 踩坑

- Python 3.12 不支持，用 3.10
- 用 `uv` 管理依赖

## License

MIT
