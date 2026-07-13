"""离线文档导入使用的递归、滑动窗口和语义切分策略。"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from typing import Literal

from langchain_core.embeddings import Embeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter


ChunkStrategy = Literal["recursive", "sliding_window", "semantic"]

_RECURSIVE_SEPARATORS = ["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""]
_SENTENCE_BOUNDARY = re.compile(r"(?<=[。！？；])")
_PARAGRAPH_BOUNDARY = re.compile(r"\n\s*\n+")


@dataclass(frozen=True)
class SourceSegment:
    """解析器输出的最小文本源单元及其页码。"""

    text: str
    page_number: int


@dataclass(frozen=True)
class ChunkSegment:
    """切分后等待 Embedding 和写入 Milvus 的文本块及其页码。"""

    text: str
    page_number: int


async def split_source_segments(
    source_segments: list[SourceSegment],
    *,
    strategy: ChunkStrategy,
    chunk_size: int,
    overlap: int,
    semantic_similarity_threshold: float,
    embedding_model: Embeddings | None,
) -> list[ChunkSegment]:
    """按指定策略切分源单元，始终保持每个源单元的页码边界。"""
    chunks: list[ChunkSegment] = []
    for source in source_segments:
        text = source.text.strip()
        if not text:
            continue

        if strategy == "recursive":
            pieces = _split_recursive(text, chunk_size=chunk_size, overlap=overlap)
        elif strategy == "sliding_window":
            pieces = _split_sliding_window(text, chunk_size=chunk_size, overlap=overlap)
        elif strategy == "semantic":
            if embedding_model is None:
                raise ValueError("semantic 策略需要 Embedding 模型")
            pieces = await _split_semantic(
                text,
                chunk_size=chunk_size,
                overlap=overlap,
                similarity_threshold=semantic_similarity_threshold,
                embedding_model=embedding_model,
            )
        else:
            raise ValueError(f"不支持的切分策略: {strategy}")

        chunks.extend(
            ChunkSegment(text=piece, page_number=source.page_number)
            for piece in pieces
            if piece
        )
    return chunks


def _split_recursive(text: str, *, chunk_size: int, overlap: int) -> list[str]:
    """使用中文分隔符优先级执行标准递归字符切分。"""
    splitter = RecursiveCharacterTextSplitter(
        separators=_RECURSIVE_SEPARATORS,
        chunk_size=chunk_size,
        chunk_overlap=overlap,
        length_function=len,
        keep_separator=True,
        is_separator_regex=False,
    )
    return [piece.strip() for piece in splitter.split_text(text) if piece.strip()]


def _split_sliding_window(text: str, *, chunk_size: int, overlap: int) -> list[str]:
    """按固定字符窗口切分，窗口间保留 overlap 字符。"""
    if chunk_size <= 0:
        raise ValueError("chunk_size 必须大于 0")
    if len(text) <= chunk_size:
        return [text]

    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        chunks.append(text[start:end])
        if end == len(text):
            break
        # overlap 配置异常时仍保证窗口向前移动，避免导入任务死循环。
        start = max(start + 1, end - overlap)
    return chunks


async def _split_semantic(
    text: str,
    *,
    chunk_size: int,
    overlap: int,
    similarity_threshold: float,
    embedding_model: Embeddings,
) -> list[str]:
    """基于相邻文本单元相似度切分，过长单元回退递归切分。"""
    units = _semantic_units(text)
    chunks: list[str] = []
    short_units: list[str] = []

    for unit in units:
        if len(unit) > chunk_size:
            if short_units:
                chunks.extend(
                    await _group_semantic_units(
                        short_units,
                        chunk_size=chunk_size,
                        similarity_threshold=similarity_threshold,
                        embedding_model=embedding_model,
                    )
                )
                short_units = []
            # 单个语义单元过长时不跨边界硬合并，回退标准递归切分。
            chunks.extend(_split_recursive(unit, chunk_size=chunk_size, overlap=overlap))
        else:
            short_units.append(unit)

    if short_units:
        chunks.extend(
            await _group_semantic_units(
                short_units,
                chunk_size=chunk_size,
                similarity_threshold=similarity_threshold,
                embedding_model=embedding_model,
            )
        )
    return chunks


def _semantic_units(text: str) -> list[str]:
    """段落优先生成语义候选单元；无段落边界时按中文句末符号拆分。"""
    paragraphs = [
        paragraph.strip()
        for paragraph in _PARAGRAPH_BOUNDARY.split(text)
        if paragraph.strip()
    ]
    if len(paragraphs) > 1:
        return paragraphs

    sentences = [
        sentence.strip()
        for sentence in _SENTENCE_BOUNDARY.split(text)
        if sentence.strip()
    ]
    return sentences or paragraphs


async def _group_semantic_units(
    units: list[str],
    *,
    chunk_size: int,
    similarity_threshold: float,
    embedding_model: Embeddings,
) -> list[str]:
    """按相邻单元相似度和最大长度聚合语义单元。"""
    if not units:
        return []
    if len(units) == 1:
        return units

    embeddings = await embedding_model.aembed_documents(units)
    chunks: list[str] = []
    current_units = [units[0]]

    for index in range(1, len(units)):
        candidate = _join_units([*current_units, units[index]])
        similarity = _cosine_similarity(embeddings[index - 1], embeddings[index])
        if len(candidate) > chunk_size or similarity < similarity_threshold:
            chunks.append(_join_units(current_units))
            current_units = [units[index]]
        else:
            current_units.append(units[index])

    chunks.append(_join_units(current_units))
    return chunks


def _join_units(units: list[str]) -> str:
    """使用空行保留候选单元的自然边界。"""
    return "\n\n".join(units)


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    """计算两个 Embedding 向量的余弦相似度。"""
    if len(left) != len(right):
        raise ValueError("Embedding 向量维度不一致")

    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return sum(a * b for a, b in zip(left, right, strict=True)) / (left_norm * right_norm)
