import logging

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings
from database import init_db
from routers import auth as auth_router, domains as domains_router, admin as admin_router
from routers import webhooks as webhooks_router
from routers import public as public_router
from scheduler import start_scheduler

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s - %(message)s")
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    start_scheduler()
    yield


app = FastAPI(title="SSL Monitor", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.FRONTEND_URL, "http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router.router)
app.include_router(domains_router.router)
app.include_router(admin_router.router)
app.include_router(webhooks_router.router)
app.include_router(public_router.router)


@app.get("/health")
async def health():
    return {"ok": True}
