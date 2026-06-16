"""TruLens Dashboard 配置与启动命令构造。"""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path


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
    """使用当前 Python 解释器启动 Streamlit，避免命中其他环境。"""
    if not options.database_url:
        raise ValueError("缺少 TRULENS_DATABASE_URL，无法启动 PostgreSQL Dashboard")

    interpreter = python_executable or sys.executable
    main_path = dashboard_main_path or str(
        Path(__file__).resolve().parents[2]
        / "RAG-assessment"
        / "trulens_dashboard_compat.py"
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


def start_dashboard(options: DashboardOptions) -> int:
    """启动 Dashboard 子进程并返回其退出码。"""
    return subprocess.run(build_dashboard_command(options), check=False).returncode
