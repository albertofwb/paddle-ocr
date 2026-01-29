# Paddle OCR

基于 PaddleOCR 的简易文字识别工具。

## 为什么造这个轮子

PaddlePaddle 的依赖安装堪称噩梦：
- Ubuntu 24.04 自带 Python 3.12，但 Paddle 不支持
- GPU 版本需要特定 CUDA 版本匹配
- 各种莫名其妙的依赖冲突

本项目通过 `uv` + 固定 Python 3.10.14 解决这些问题。

## 环境要求

- Linux (已配置清华镜像源 + Paddle 官方 GPU 源)
- CUDA 12.6 (如需 GPU 加速)
- [uv](https://github.com/astral-sh/uv) 包管理器

## 安装

```bash
# 克隆项目
git clone https://github.com/BabyNine0515/paddle-ocr.git
cd paddle-ocr

# 安装依赖 (uv 会自动创建 Python 3.10.14 虚拟环境)
uv sync
```

## 使用

```bash
# 识别图片 (默认 t1.jpg)
PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True uv run python main.py

# 指定图片路径
PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True uv run python main.py /path/to/image.jpg
```

## 输出格式

```
(左上角x,左上角y) (右下角x,右下角y) | 识别文字
```

示例：
```
(100,50) (300,80) | Hello World
(100,100) (250,130) | 你好世界
```

## 备注

实测 GPU 版本对比 CPU 版本速度提升有限，单张图片推理时差异不大。批量处理时 GPU 优势更明显。
