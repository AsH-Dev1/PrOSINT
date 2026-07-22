import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from web.routes import router, pages_router

app = FastAPI(
    title="PrOSINT",
    description="OSINT Multi-Source Tool - Web Interface",
    version="1.0.0",
)

static_dir = Path(__file__).resolve().parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

app.include_router(pages_router)
app.include_router(router)
