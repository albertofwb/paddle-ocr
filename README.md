# Paddle OCR 浏览器自动化

用 PaddleOCR + Playwright 实现基于视觉的浏览器自动化。

## 为什么？

- **省 Token**: DOM snapshot 动辄上万 tokens，OCR 输出只有几十行
- **不依赖 DOM**: 网页结构变化不影响，只要文字还在就能找到
- **本地运行**: OCR 完全本地，0 API 消耗

## 安装

```bash
# 需要 Python 3.10 (Paddle 不支持 3.12)
uv sync
```

## 使用

### 基础 OCR

```bash
# 识别本地图片
./ocr.sh screenshot.png

# 查找特定文字
./ocr.sh screenshot.png -t "登录"

# 精确匹配
./ocr.sh screenshot.png -t "Post" --exact

# JSON 输出
./ocr.sh screenshot.png --json
```

### 连接浏览器 (CDP)

```bash
# 截取当前浏览器页面并 OCR
./ocr.sh --cdp

# 查找文字
./ocr.sh --cdp -t "发布"

# 查找并点击！
./ocr.sh --cdp -t "发布" --click

# 精确匹配点击 (避免 "Post" 匹配到 "118 posts")
./ocr.sh --cdp -t "Post" --exact --click
```

### 快捷点击

```bash
# 一键查找并点击
./click.sh "发布"
./click.sh "Post" --exact
```

### Python API

```python
from ocr import recognize, find_text, find_text_item

# 识别所有文字
items = recognize("screenshot.png")
for item in items:
    print(f"{item['center']} | {item['text']}")

# 查找文字
coord = find_text("screenshot.png", "登录")
print(f"点击坐标: {coord}")

# 获取完整信息
item = find_text_item("screenshot.png", "登录", exact=True)
print(f"文字: {item['text']}, 边界: {item['bbox']}, 中心: {item['center']}")
```

### 配合 Clawdbot

```python
import asyncio
from main import ocr_and_click

# 截图 + OCR + 点击
coord = asyncio.run(ocr_and_click(
    cdp_url="http://127.0.0.1:18800",
    target="发布",
    exact=True
))
if coord:
    print(f"已点击 {coord}")
```

## 输出格式

```
(x1,y1) (x2,y2) | 识别的文字
```

- `(x1,y1)`: 左上角坐标
- `(x2,y2)`: 右下角坐标
- 中心点 = `((x1+x2)/2, (y1+y2)/2)`

## 踩坑记录

1. **PaddlePaddle 安装**: 用 `uv` 管理依赖，比 pip 靠谱
2. **Python 3.12**: 不支持！用 3.10
3. **GPU vs CPU**: 几乎没区别，小任务 CPU 够用

## License

MIT
