import base64
import sys
from pathlib import Path

import anyio
from mcp.server.fastmcp import FastMCP

from app import config, pipeline
from app.schemas import AnalysisResponse

mcp = FastMCP("contract-analyzer", host=config.MCP_HOST, port=config.MCP_PORT)


def run(data) -> AnalysisResponse:
    try:
        return pipeline.analyze(data)
    except pipeline.AnalyzeError as e:
        raise ValueError(f"{e.status}: {e.message}")


@mcp.tool()
async def analyze_contract_file(path: str) -> AnalysisResponse:
    """Анализ PDF договора по пути на диске."""
    if not config.MCP_ALLOWED_DIR:
        raise ValueError("Доступ к файлам выключен: задайте MCP_ALLOWED_DIR")
    root = Path(config.MCP_ALLOWED_DIR).resolve()
    file = Path(path).expanduser().resolve()
    if not file.is_relative_to(root):
        raise ValueError("Путь вне разрешённой папки")
    if not file.is_file():
        raise ValueError("Файл не найден")
    if file.stat().st_size > pipeline.MAX_SIZE:
        raise ValueError("413: Файл слишком большой")
    return await anyio.to_thread.run_sync(run, file.read_bytes())


@mcp.tool()
async def analyze_contract_base64(pdf_base64: str) -> AnalysisResponse:
    """Анализ PDF договора в base64."""
    try:
        data = base64.b64decode(pdf_base64, validate=True)
    except Exception:
        raise ValueError("Некорректный base64")
    return await anyio.to_thread.run_sync(run, data)


if __name__ == "__main__":
    mcp.run(transport=sys.argv[1] if len(sys.argv) > 1 else "stdio")
