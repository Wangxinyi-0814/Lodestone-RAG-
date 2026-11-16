"""临时测试脚本：测各阶段延迟"""
import asyncio
import time
from quarry.infra.db import init_pool, close_pool, acquire
from quarry.retrieval.pg.searcher import hybrid_search


async def main():
    await init_pool()
    try:
        # 拿 collection_id
        async with acquire() as conn:
            row = await conn.fetchrow(
                "SELECT id FROM collections WHERE slug='travel-guide' AND status='active'"
            )
            coll_id = row["id"]
        print(f"collection_id: {coll_id}")

        # 测5次完整 recall
        print("\n=== recall 阶段（embed + SQL）===")
        times = []
        for i in range(5):
            t0 = time.perf_counter()
            hits = await hybrid_search(
                collection_id=coll_id,
                query="山塘街的开放时间",
                caller_labels=["public"],
                dense_k=50,
                sparse_k=50,
                top_k=15,
            )
            dt = (time.perf_counter() - t0) * 1000
            times.append(dt)
            print(f"  第{i+1}次: {dt:.1f} ms, 返回 {len(hits)} 条")
        print(f"  平均: {sum(times)/len(times):.1f} ms")

        # 测 expand 阶段（查 parents + neighbors + docs）
        print("\n=== expand 阶段 ===")
        from quarry.context.expand import fetch_parents, fetch_neighbors

        picked_parent_ids = [h.parent_id for h in hits[:5]]
        expand_times = []
        for i in range(5):
            t0 = time.perf_counter()
            async with acquire() as conn:
                parents = await fetch_parents(conn, coll_id, picked_parent_ids, ["public"])
                neighbors = await fetch_neighbors(
                    conn, coll_id, list(parents.values()), 1, ["public"]
                )
            dt = (time.perf_counter() - t0) * 1000
            expand_times.append(dt)
            print(f"  第{i+1}次: {dt:.1f} ms, parents={len(parents)}, neighbors={len(neighbors)}")
        print(f"  平均: {sum(expand_times)/len(expand_times):.1f} ms")

    finally:
        await close_pool()


if __name__ == "__main__":
    asyncio.run(main())
