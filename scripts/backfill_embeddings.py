"""
One-time script to embed all existing jobs that don't yet have embeddings.
Useful after changing the embedding model.

Usage:
    DATABASE_URL=postgresql+asyncpg://... python scripts/backfill_embeddings.py
"""
import asyncio
import sys, os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from sqlalchemy import select
from app.database import AsyncSessionLocal
from app.models.job import Job
from app.services.embedding import embed_job


async def main():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Job).where(Job.embedding == None))
        jobs = result.scalars().all()
        print(f"Embedding {len(jobs)} jobs...")
        for i, job in enumerate(jobs):
            job.embedding = embed_job(job)
            if i % 100 == 0:
                await db.commit()
                print(f"  {i}/{len(jobs)}")
        await db.commit()
        print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
