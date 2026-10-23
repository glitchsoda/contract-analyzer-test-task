import asyncio
from pathlib import Path

from arq.connections import RedisSettings

from app import config, pipeline


async def analyze_job(ctx, path) -> dict:
    path = Path(path)
    try:
        resp = await asyncio.to_thread(pipeline.analyze, path.read_bytes())
        return {"result": resp.model_dump()}
    except pipeline.AnalyzeError as e:
        return {"error": e.message, "status": e.status}
    finally:
        path.unlink(missing_ok=True)


class WorkerSettings:
    functions = [analyze_job]
    redis_settings = RedisSettings.from_dsn(config.REDIS_URL)
    max_jobs = config.WORKER_MAX_JOBS
    job_timeout = 900
    keep_result = 3600
