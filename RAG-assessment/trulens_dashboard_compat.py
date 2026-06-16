"""TruLens Dashboard 的 Windows Trends 页面兼容启动器。"""

from __future__ import annotations

import atexit
import shutil
from pathlib import Path


_RUNTIME_DIRECTORY: Path | None = None


def _prepare_trends_page() -> Path:
    """生成仅修正 Windows 日期格式的临时 Trends 页面副本。"""
    global _RUNTIME_DIRECTORY

    from importlib.resources import files

    source_path = files("trulens.dashboard.tabs").joinpath("Trends.py")
    source = source_path.read_text(encoding="utf-8")
    if "%-d" not in source:
        return Path(str(source_path))

    if _RUNTIME_DIRECTORY is None:
        runtime_directory = Path(__file__).resolve().parents[1] / ".trulens-dashboard-runtime"
        runtime_directory.mkdir(parents=True, exist_ok=True)
        _RUNTIME_DIRECTORY = runtime_directory
        atexit.register(shutil.rmtree, _RUNTIME_DIRECTORY, ignore_errors=True)

    patched_path = _RUNTIME_DIRECTORY / "Trends.py"
    patched_path.write_text(
        source.replace("%-d", "%#d"),
        encoding="utf-8",
        newline="\n",
    )
    return patched_path


def _patch_decimal_quantile() -> None:
    """将 PostgreSQL Decimal 序列转换为 float，避免 NumPy 分位数计算失败。"""
    from decimal import Decimal

    import pandas as pd

    original_quantile = pd.Series.quantile
    if getattr(original_quantile, "_yyy_rag_decimal_compatible", False):
        return

    def decimal_compatible_quantile(self, *args, **kwargs):
        """兼容 TruLens 延迟字段从 PostgreSQL 返回 Decimal 的情况。"""
        values = self.dropna()
        if any(isinstance(value, Decimal) for value in values):
            return original_quantile(self.astype("float64"), *args, **kwargs)
        return original_quantile(self, *args, **kwargs)

    decimal_compatible_quantile._yyy_rag_decimal_compatible = True
    pd.Series.quantile = decimal_compatible_quantile


def _patch_dashboard_navigation() -> None:
    """让官方导航在 Windows 中加载修正后的 Trends 页面。"""
    import trulens.dashboard.main as dashboard_main

    original_page = dashboard_main.st.Page
    patched_trends_page = _prepare_trends_page()
    _patch_decimal_quantile()

    def create_page(path: str, *args, **kwargs):
        """仅替换官方 Trends 页面，其他页面保持原样。"""
        if Path(path).name == "Trends.py":
            path = str(patched_trends_page)
        return original_page(path, *args, **kwargs)

    dashboard_main.st.Page = create_page


def main() -> None:
    """应用 Windows 兼容处理后运行官方 TruLens Dashboard。"""
    import trulens.dashboard.main as dashboard_main

    _patch_dashboard_navigation()
    dashboard_main.main()


if __name__ == "__main__":
    main()
