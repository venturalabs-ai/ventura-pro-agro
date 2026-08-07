"""Aplicação FastAPI do Ventura Pro Agro (API + estáticos do frontend)."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Garante diretórios de runtime.
    _ = (settings.cache_dir, settings.db_path)
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description=(
        "Planejamento da melhor época de plantio e colheita por município no Brasil: "
        "clima (previsão + 10 anos de normais), fase da lua, maré, barômetro, "
        "ZARC regional e estimativa de custos por alqueire/ha/acre/m²."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # desktop/mobile locais: origens variadas (file://, capacitor://)
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix=settings.api_prefix)

# Frontend SPA (index.html) — servido quando existe.
if settings.frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(settings.frontend_dir), html=True), name="frontend")
