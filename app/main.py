from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse

from app import cache, config, pipeline
from app.schemas import AnalysisResponse

STATIC = Path(__file__).parent / "static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.redis = None
    if config.ASYNC_ENABLED:
        from arq import create_pool
        from arq.connections import RedisSettings
        app.state.redis = await create_pool(RedisSettings.from_dsn(config.REDIS_URL))
    yield
    if app.state.redis:
        await app.state.redis.aclose()


app = FastAPI(title="Contract Analyzer", version="0.3.0", lifespan=lifespan)


def get_redis(request):
    return getattr(request.app.state, "redis", None)


async def read_upload(file) -> bytes:
    data = await file.read(pipeline.MAX_SIZE + 1)
    if len(data) > pipeline.MAX_SIZE:
        raise HTTPException(413, "Файл слишком большой")
    return data


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/health")
def health(request: Request):
    return {"status": "ok", "async": bool(get_redis(request))}


@app.post("/analyze", response_model=AnalysisResponse)
async def analyze(file: UploadFile = File(...)):
    data = await read_upload(file)
    try:
        return await run_in_threadpool(pipeline.analyze, data)
    except pipeline.AnalyzeError as e:
        raise HTTPException(e.status, e.message)


def job_error(info) -> str | None:
    result = info.result if info else None
    if info and info.success and isinstance(result, dict) and "error" not in result:
        return None
    return result.get("error") if isinstance(result, dict) else "Внутренняя ошибка"


@app.post("/jobs", status_code=202)
async def create_job(request: Request, file: UploadFile = File(...)):
    from arq.constants import result_key_prefix
    from arq.jobs import Job, JobStatus

    redis = get_redis(request)
    if redis is None:
        raise HTTPException(503, "Асинхронный режим выключен (ASYNC_ENABLED=false)")

    data = await read_upload(file)
    try:
        pipeline.check_pdf(data)
    except pipeline.AnalyzeError as e:
        raise HTTPException(e.status, e.message)

    sha = cache.sha256(data)
    path = Path(config.UPLOAD_DIR) / f"{sha}.pdf"
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_bytes(data)

    job = await redis.enqueue_job("analyze_job", str(path), _job_id=sha)
    if job is None:
        existing = Job(sha, redis)
        if await existing.status() == JobStatus.complete:
            if job_error(await existing.result_info()) is None:
                path.unlink(missing_ok=True)
            else:
                await redis.delete(result_key_prefix + sha)
                await redis.enqueue_job("analyze_job", str(path), _job_id=sha)

    return {"job_id": sha, "status_url": f"/jobs/{sha}"}


@app.get("/jobs/{job_id}")
async def get_job(request: Request, job_id: str):
    from arq.jobs import Job, JobStatus

    redis = get_redis(request)
    if redis is None:
        raise HTTPException(503, "Асинхронный режим выключен")

    job = Job(job_id, redis)
    status = await job.status()
    if status == JobStatus.not_found:
        raise HTTPException(404, "Задача не найдена")
    if status != JobStatus.complete:
        return {"job_id": job_id, "status": status.value}

    info = await job.result_info()
    if (error := job_error(info)) is not None:
        return {"job_id": job_id, "status": "failed", "error": error}
    return {"job_id": job_id, "status": "complete", "result": info.result["result"]}
