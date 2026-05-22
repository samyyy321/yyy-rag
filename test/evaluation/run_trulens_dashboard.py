"""在 yyy-rag 主环境中启动连接 PostgreSQL 的 TruLens 仪表盘。"""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[2]
TRULENS_DATABASE_PREFIX = "trulens_"


@dataclass(frozen=True)
class DashboardOptions:
    """启动 Dashboard 所需的最小配置。"""

    database_url: str
    host: str
    port: int


def get_dashboard_options(
    *,
    environ: Mapping[str, str] | None = None,
) -> DashboardOptions:
    """读取并校验 Dashboard 配置，默认仅监听本地回环地址。"""
    values = os.environ if environ is None else environ
    database_url = values.get("TRULENS_DATABASE_URL", "").strip()
    host = values.get("TRULENS_DASHBOARD_HOST", "127.0.0.1").strip()
    raw_port = values.get("TRULENS_DASHBOARD_PORT", "8501").strip()
    if not host:
        raise ValueError("Dashboard 监听地址不能为空")
    try:
        port = int(raw_port)
    except ValueError as exc:
        raise ValueError("Dashboard 端口必须是 1 到 65535 的整数") from exc
    if not 1 <= port <= 65535:
        raise ValueError("Dashboard 端口必须是 1 到 65535 的整数")
    return DashboardOptions(database_url=database_url, host=host, port=port)


def build_dashboard_command(
    options: DashboardOptions,
    *,
    python_executable: str | None = None,
    dashboard_main_path: str | None = None,
) -> list[str]:
    """使用当前 Python 解释器启动 Streamlit，避免错误命中 PATH 中的其他环境。"""
    if not options.database_url:
        raise ValueError("缺少 TRULENS_DATABASE_URL，无法启动 PostgreSQL Dashboard")

    interpreter = python_executable or sys.executable
    main_path = dashboard_main_path or str(
        files("trulens.dashboard").joinpath("main.py")
    )
    return [
        interpreter,
        "-m",
        "streamlit",
        "run",
        "--server.headless=True",
        "--server.fileWatcherType=none",
        "--client.toolbarMode=viewer",
        f"--server.address={options.host}",
        f"--server.port={options.port}",
        main_path,
        "--",
        "--database-url",
        options.database_url,
        "--database-prefix",
        TRULENS_DATABASE_PREFIX,
    ]


def main() -> int:
    """加载项目 .env 后，在主环境中启动 TruLens Dashboard。"""
    load_dotenv(PROJECT_ROOT / ".env")
    options = get_dashboard_options()
    return subprocess.run(build_dashboard_command(options), check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
