"""第六章新增的红线：事实层不能绕过权限；关掉事实层时上下文必须是原文。"""
import pytest

import quarry.infra.embed as embed
from quarry.facts.attach import fetch_mentions
from quarry.infra.db import acquire, close_pool, init_pool
from quarry.pipeline import search_evidence
from quarry.rerank import reset_reranker


@pytest.fixture(autouse=True)
async def db_pool():
    embed._embedder = None
    reset_reranker()
    await init_pool()
    yield
    await close_pool()


async def test_mentions_follow_chunk_acl():
    """红线 8  调用方标签和块的权限标签不相交，一条提及都拿不到；相交则能拿到。"""
    async with acquire() as conn:
        coll_id = await conn.fetchval(
            "SELECT id FROM collections WHERE slug = 'travel-guide'")
        ids = [r["chunk_id"] for r in await conn.fetch(
            "SELECT DISTINCT chunk_id FROM fact_mentions WHERE collection_id = $1 LIMIT 20",
            coll_id)]
        assert ids, "fact_mentions 是空的，先跑 6.3 的抽取"
        assert await fetch_mentions(conn, coll_id, ids, ["nobody"]) == []
        assert await fetch_mentions(conn, coll_id, ids, ["public"]), "有权限却拿不到提及"


async def test_use_facts_false_keeps_original_context():
    """红线 9  关掉事实层，上下文里不能出现占位符，证据里也不能带事实。"""
    r = await search_evidence("travel-guide", "门票多少钱", caller_labels=["public"],
                              use_facts=False)
    assert r.evidences
    assert all("〔F" not in e.context and not e.facts for e in r.evidences)