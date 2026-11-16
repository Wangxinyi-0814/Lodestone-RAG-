import asyncio
from uuid import UUID
from quarry.infra.db import acquire, init_pool, close_pool

async def check():
    await init_pool()
    async with acquire() as conn:
        row = await conn.fetchrow(
            "SELECT id, source_uri, status FROM documents WHERE id = $1",
            UUID("867fed23-0319-41c4-a4dd-eca4ee0046ff")
        )
        print(row)
    await close_pool()

if __name__ == "__main__":
    asyncio.run(check())
