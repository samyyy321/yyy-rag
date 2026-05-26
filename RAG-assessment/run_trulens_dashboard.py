"""在 yyy-rag 主环境中启动连接 PostgreSQL 的 TruLens Dashboard。"""

from __future__ import annotations

import sys
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from src.evaluation.trulens_dashboard import get_dashboard_options, start_dashboard


if __name__ == "__main__":
    load_dotenv(PROJECT_ROOT / ".env")
    raise SystemExit(start_dashboard(get_dashboard_options()))
