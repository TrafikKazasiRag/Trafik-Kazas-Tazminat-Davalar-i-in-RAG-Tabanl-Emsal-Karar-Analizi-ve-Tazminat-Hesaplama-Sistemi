"""main.py: FastAPI ana uygulama çatısı."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from trafikrag.api.routers import analyze

app = FastAPI(
    title="Trafik Kazası Tazminat RAG & Analiz API",
    version="1.0.0",
    description="Emsal karar analizi ve deterministik tazminat hesaplama sistemi API'si.",
)

# React + Vite frontend erişimi için CORS ayarı
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Router'ı ekle
app.include_router(analyze.router, prefix="/api")


@app.get("/api/health", tags=["System"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "trafikrag-api"}