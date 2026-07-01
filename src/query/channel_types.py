"""多通道检索在融合前使用的统一证据数据类型。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


@dataclass(frozen=True)
class ChannelEvidence:
    """一个检索通道返回的可供回答模型使用的证据文本和原始记录。"""

    channel: Literal["document", "graph", "sql"]
    content: str
    records: tuple[dict[str, Any], ...] = ()
