from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
from typing import Optional

# ← ESTO ES IMPORTANTE: debe llamarse "app"
app = FastAPI(title="KinetsuList API")

# Montar archivos estáticos
app.mount("/static", StaticFiles(directory="static"), name="static")

# Configurar templates
templates = Jinja2Templates(directory="templates")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Endpoints
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Renderizar la página principal"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/animes")
def get_animes(limit: int = 50, offset: int = 0):
    return {
        "total": 0,
        "animes": [],
        "offset": offset,
        "limit": limit
    }

@app.get("/api/mi-lista")
def get_mi_lista():
    return {"animes": []}

@app.get("/api/proyectar-exito")
def proyectar_exito(limit: int = 10):
    return {"trending": []}

@app.get("/api/pronostico-rating")
def pronostico_rating(min_rating: float = 8.0, limit: int = 20):
    return {"high_rated": []}

@app.get("/api/mapa-nichos")
def mapa_nichos():
    return {"genres": ["Acción", "Romance", "Comedia", "Fantasía", "Aventura"]}

@app.get("/api/adn-contenido/{anime_id}")
def adn_contenido(anime_id: int):
    return {
        "anime_id": anime_id,
        "analysis": "Análisis detallado aquí"
    }

@app.get("/api/joyas-ocultas")
def joyas_ocultas(limit: int = 20):
    return {"hidden_gems": []}