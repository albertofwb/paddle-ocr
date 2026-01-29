## Project Rules

1. Always use `uv` to manage dependencies instead of pip
   ```bash
   # Create venv and sync dependencies from pyproject.toml
   uv sync

   # Add new dependency
   uv add <package>

   # Run script
   uv run python main.py
   ```

2. Run OCR with environment variable:
   ```bash
   PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True uv run python main.py
   ```
