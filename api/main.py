from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import os

from db import get_pool, close_pool
from routers import overview, classes, scores, messages, alerts, students, upload


@asynccontextmanager
async def lifespan(app: FastAPI):
    await get_pool()          # warm up connection pool on startup
    yield
    await close_pool()        # clean up on shutdown


app = FastAPI(title="AttendIQ Dashboard API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # tighten this when deploying to Azure
    allow_methods=["GET"],
    allow_headers=["*"],
)

# API routes
app.include_router(overview.router, prefix="/api")
app.include_router(classes.router,  prefix="/api")
app.include_router(scores.router,   prefix="/api")
app.include_router(messages.router, prefix="/api")
app.include_router(alerts.router,    prefix="/api")
app.include_router(students.router,  prefix="/api")
app.include_router(upload.router,    prefix="/api")

# Serve the dashboard HTML at /
DASH_DIR = os.path.join(os.path.dirname(__file__), "..")
app.mount("/static", StaticFiles(directory=DASH_DIR), name="static")


@app.get("/")
async def dashboard():
    return FileResponse(os.path.join(DASH_DIR, "index.html"))

@app.get("/students")
async def students_page():
    return FileResponse(os.path.join(DASH_DIR, "students.html"))

@app.get("/upload")
async def upload_page():
    return FileResponse(os.path.join(DASH_DIR, "upload.html"))
