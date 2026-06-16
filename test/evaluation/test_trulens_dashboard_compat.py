"""TruLens Dashboard Windows 日期格式兼容测试。"""

import importlib.util
from pathlib import Path


_MODULE_PATH = Path(__file__).parents[2] / "RAG-assessment" / "trulens_dashboard_compat.py"
_SPEC = importlib.util.spec_from_file_location("trulens_dashboard_compat", _MODULE_PATH)
assert _SPEC is not None and _SPEC.loader is not None
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)


def test_trends_page_replaces_unix_only_date_format() -> None:
    """生成的 Trends 页面不能继续包含 Windows 不支持的 %-d。"""
    patched_path = _MODULE._prepare_trends_page()
    source = patched_path.read_text(encoding="utf-8")

    assert "%-d" not in source
    assert "%#d" in source


def test_decimal_series_quantile_is_converted_before_numpy_interpolation(monkeypatch) -> None:
    """Trends 的延迟分位数计算必须兼容 PostgreSQL Decimal 值。"""
    from decimal import Decimal

    import pandas as pd

    original_quantile = pd.Series.quantile
    _MODULE._patch_decimal_quantile()
    try:
        result = pd.Series([Decimal("1.2"), Decimal("2.4")]).quantile(0.9)
    finally:
        monkeypatch.setattr(pd.Series, "quantile", original_quantile)

    assert isinstance(result, float)
    assert result > 2.0
