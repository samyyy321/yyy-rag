import pytest

from src.index.chunking import SourceSegment, split_source_segments


@pytest.mark.asyncio
async def test_recursive_split_prefers_chinese_paragraph_and_sentence_boundaries():
    """递归切分应在中文段落和句末符号边界优先断开。"""
    source_segments = [
        SourceSegment(
            text="第一段内容。第二句内容。\n\n第二段内容。第三句内容。",
            page_number=0,
        )
    ]

    chunks = await async_split(source_segments, strategy="recursive", chunk_size=12, overlap=2)

    assert chunks
    assert all(len(chunk.text) <= 12 for chunk in chunks)
    assert any("\n\n" in chunk.text or chunk.text.endswith(("。", "！", "？")) for chunk in chunks)


@pytest.mark.asyncio
async def test_sliding_window_keeps_configured_overlap_without_redundant_tail():
    """滑动窗口应按固定窗口和 overlap 前进，末尾不重复。"""
    source_segments = [SourceSegment(text="abcdefghijklmn", page_number=2)]

    chunks = await async_split(source_segments, strategy="sliding_window", chunk_size=6, overlap=2)

    assert [chunk.text for chunk in chunks] == ["abcdef", "efghij", "ijklmn"]
    assert chunks[0].text[-2:] == chunks[1].text[:2]
    assert chunks[1].text[-2:] == chunks[2].text[:2]


class FakeEmbeddings:
    """提供可预测向量的最小语义切分 Embedding 替身。"""

    async def aembed_documents(self, texts):
        vectors = {
            "甲": [1.0, 0.0],
            "乙": [0.9, 0.1],
            "丙": [0.0, 1.0],
        }
        return [vectors[text] for text in texts]


@pytest.mark.asyncio
async def test_semantic_split_breaks_at_low_similarity_boundary():
    """相邻单元相似度低于阈值时应形成新的语义 chunk。"""
    chunks = await split_source_segments(
        [SourceSegment(text="甲\n\n乙\n\n丙", page_number=3)],
        strategy="semantic",
        chunk_size=20,
        overlap=2,
        semantic_similarity_threshold=0.5,
        embedding_model=FakeEmbeddings(),
    )

    assert [chunk.text for chunk in chunks] == ["甲\n\n乙", "丙"]


@pytest.mark.asyncio
async def test_semantic_split_falls_back_to_recursive_for_long_source_unit():
    """超过最大长度的语义单元应回退递归切分，而不是超过限制。"""
    chunks = await split_source_segments(
        [SourceSegment(text="很" * 14, page_number=4)],
        strategy="semantic",
        chunk_size=5,
        overlap=1,
        semantic_similarity_threshold=0.5,
        embedding_model=FakeEmbeddings(),
    )

    assert len(chunks) > 1
    assert all(len(chunk.text) <= 5 for chunk in chunks)
    assert all(chunk.page_number == 4 for chunk in chunks)


@pytest.mark.asyncio
async def test_split_never_merges_different_page_source_segments():
    """任意策略都必须在页码源单元边界断开。"""
    chunks = await split_source_segments(
        [
            SourceSegment(text="第一页内容", page_number=1),
            SourceSegment(text="第二页内容", page_number=2),
        ],
        strategy="sliding_window",
        chunk_size=20,
        overlap=2,
        semantic_similarity_threshold=0.5,
        embedding_model=None,
    )

    assert [(chunk.text, chunk.page_number) for chunk in chunks] == [
        ("第一页内容", 1),
        ("第二页内容", 2),
    ]


async def async_split(source_segments, *, strategy, chunk_size, overlap):
    """为同步策略测试复用同一个异步分发器。"""
    return await split_source_segments(
        source_segments,
        strategy=strategy,
        chunk_size=chunk_size,
        overlap=overlap,
        semantic_similarity_threshold=0.5,
        embedding_model=None,
    )
