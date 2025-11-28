from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import joblib
import os
from pathlib import Path
import json
from pydantic import BaseModel
from typing import List, Optional

# =====================================================================
# 1. CONFIGURACIÓN INICIAL Y CARGA DE RECURSOS
# =====================================================================

BASE_DIR = Path(__file__).resolve().parent
MODEL_DIR = BASE_DIR / "models" / "clasificacion"
DATA_DIR = BASE_DIR / "data"

id_usuario = 1266997   

# 1.2. Carga de recursos
try:
    print("📂 Cargando recursos...")

    # 1. CLASIFICACIÓN
    with open(MODEL_DIR / "modelos_clasificacion.pkl", "rb") as f:
        modelos_cargados = joblib.load(f)
    modelo_clasificacion = modelos_cargados["RandomForest"]
    
    with open(MODEL_DIR / "scaler_clasificacion.pkl", "rb") as f:
        scaler_clasificacion = joblib.load(f)

    with open(MODEL_DIR / "columnas_entrenamiento_clasificacion.json", "r") as f:
        FEATURES_FINALES = json.load(f)

    df_clasificacion = pd.read_parquet(DATA_DIR / "final_anime_dataset_clasificacion.parquet")

    # 2. REGRESIÓN
    with open(BASE_DIR / "models" / "regresion" / "modelo_regresion.pkl", "rb") as f:
        modelos_regresion_cargados = joblib.load(f)
    modelo_regresion = modelos_regresion_cargados["RandomForest"]

    with open(BASE_DIR / "models" / "regresion" / "scaler_regresion.pkl", "rb") as f:
        scaler_regresion = joblib.load(f)

    with open(BASE_DIR / "models" / "regresion" / "columnas_entrenamiento_regresion.json", "r") as f:
        FEATURES_REGRESION_FINALES = json.load(f)

    df_regresion = pd.read_parquet(DATA_DIR / "final_anime_dataset_regresion.parquet")

    # 3. CLUSTERING (SOLUCIÓN AL ERROR)
    # En lugar de cargar el modelo .pkl que falla, cargamos el dataset que YA TIENE los clusters
    # Asegúrate de que el nombre del archivo coincida con el que tienes en la carpeta data
    path_clustering_data = DATA_DIR / "final_anime_dataset_clustering.parquet"
    if path_clustering_data.exists():
        print(f"📂 Cargando datos pre-calculados de clustering: {path_clustering_data.name}")
        df_clustering = pd.read_parquet(path_clustering_data)
    else:
        print("⚠️ No se encontró el dataset de clustering. Usaremos el de clasificación como fallback.")
        df_clustering = df_clasificacion.copy()

    # 4. IMÁGENES
    df_imagenes = pd.read_csv(DATA_DIR / "imagenes.csv")
    if 'anime_id' in df_imagenes.columns and 'Image URL' in df_imagenes.columns:
        df_imagenes = df_imagenes[['anime_id', 'Image URL']].copy()
        df_imagenes.rename(columns={'Image URL': 'image_url'}, inplace=True)
    
    print("✅ TODOS los recursos cargados correctamente.")

except FileNotFoundError as e:
    print(f"❌ ERROR CRÍTICO: No se encontró un archivo: {e.filename}")
    raise
except KeyError as e:
    print(f"❌ ERROR CRÍTICO: Clave faltante en diccionario: {e}")
    raise
except Exception as e:
    print(f"❌ ERROR CRÍTICO GENERAL: {e}")
    raise

# =====================================================================
# 2. CONFIGURACIÓN DE FASTAPI
# =====================================================================

app = FastAPI(
    title="KitsuneList API",
    description="API de recomendaciones de anime con ML",
    version="2.0.0"
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =====================================================================
# 3. FUNCIÓN AUXILIAR PARA AGREGAR image_url
# =====================================================================

def agregar_imagenes_csv(df, columna_id='id_anime'):
    df = df.copy()
    
    # Merge con el dataframe de imágenes por anime_id
    df_merged = df.merge(
        df_imagenes[['anime_id', 'image_url']], 
        left_on=columna_id, 
        right_on='anime_id', 
        how='left'
    )
    
    placeholder_url = "https://via.placeholder.com/300x450?text=No+Image"
    df_merged['image_url'] = df_merged['image_url'].fillna(placeholder_url)
    
    # Limpieza de columnas duplicadas
    if 'anime_id' in df_merged.columns and 'anime_id' != columna_id:
        cols_to_drop = [col for col in df_merged.columns if col == 'anime_id' and col != columna_id]
        if cols_to_drop:
            df_merged = df_merged.drop(columns=cols_to_drop)
    
    return df_merged

# =====================================================================
# 4. ENDPOINTS PÚBLICOS
# =====================================================================

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    try:
        app_js_mtime = int(os.path.getmtime(BASE_DIR / "static" / "js" / "app.js"))
    except Exception:
        app_js_mtime = 0

    return templates.TemplateResponse(
        "index.html", 
        {"request": request, "app_version": app_js_mtime}
    )

@app.get("/api/recomendaciones")
def recomendar(id_usuario: int = id_usuario, limit: int = 10):
    # Obtener datos del usuario
    df_user_data = df_clasificacion[df_clasificacion["id_usuario"] == id_usuario].copy()

    if df_user_data.empty:
        raise HTTPException(status_code=404, detail=f"Usuario {id_usuario} no encontrado.")

    df_todos_animes = df_clasificacion.drop_duplicates(subset=['id_anime']).copy()
    animes_vistos = set(df_user_data["id_anime"].unique())
    df_candidatos = df_todos_animes[~df_todos_animes["id_anime"].isin(animes_vistos)].copy()
    
    if df_candidatos.empty:
        return {"recomendaciones": []}
    
    df_respuesta = df_candidatos.copy()
    user_profile = df_user_data.iloc[0]
    
    # Actualizar características del usuario
    for col in FEATURES_FINALES:
        if col in user_profile.index:
            if col.startswith('genero_preferido_') or col in ['puntuacion_promedio_usuario', 'Matches_Preferred_Genre']:
                df_respuesta[col] = user_profile[col]
    
    # Predecir
    X_prediccion = df_respuesta[FEATURES_FINALES].copy()
    X_prediccion_escalada = scaler_clasificacion.transform(X_prediccion)
    df_respuesta["probabilidad_interes"] = modelo_clasificacion.predict_proba(X_prediccion_escalada)[:, 1]
    
    COLUMNAS_RESPUESTA = [
        "id_anime", "titulo_anime", "nombre_anime", "puntuacion", 
        "total_episodios", "popularidad", "favoritos", "probabilidad_interes", "sinopsis"
    ]
    
    for col in COLUMNAS_RESPUESTA:
        if col not in df_respuesta.columns:
            df_respuesta[col] = ""
    
    df_respuesta = df_respuesta[COLUMNAS_RESPUESTA].copy()
    df_respuesta = agregar_imagenes_csv(df_respuesta)

    recomendados = (
        df_respuesta.sort_values("probabilidad_interes", ascending=False)
        .head(limit)
        .to_dict(orient="records") 
    )
    
    return {"recomendaciones": recomendados}


@app.get("/api/predecir-anime/{anime_id}")
def predecir_anime(anime_id: int, id_usuario: int = None):
    if id_usuario is None:
        id_usuario = 1266997
    
    df_user_data = df_clasificacion[df_clasificacion["id_usuario"] == id_usuario].copy()
    if df_user_data.empty:
        raise HTTPException(status_code=404, detail=f"Usuario {id_usuario} no encontrado")
    
    df_anime = df_clasificacion[df_clasificacion["id_anime"] == anime_id].drop_duplicates(subset=['id_anime']).copy()
    if df_anime.empty:
        raise HTTPException(status_code=404, detail=f"Anime {anime_id} no encontrado")
    
    df_prediccion = df_anime.copy()
    user_profile = df_user_data.iloc[0]
    
    for col in FEATURES_FINALES:
        if col in user_profile.index:
            if col.startswith('genero_preferido_') or col in ['puntuacion_promedio_usuario', 'Matches_Preferred_Genre']:
                df_prediccion[col] = user_profile[col]
    
    try:
        X_pred = df_prediccion[FEATURES_FINALES].copy()
        X_pred_scaled = scaler_clasificacion.transform(X_pred)
        prob = modelo_clasificacion.predict_proba(X_pred_scaled)[0][1]
        prediccion = "Sí" if prob >= 0.5 else "No"
        
        titulo = str(df_anime['titulo_anime'].values[0]) if 'titulo_anime' in df_anime.columns else "Sin título"

        return {
            "anime_id": int(anime_id),
            "titulo": titulo,
            "probabilidad": float(prob),
            "porcentaje": f"{prob*100:.1f}%",
            "prediccion": str(prediccion),
            "mensaje": f"Hay un {prob*100:.1f}% de probabilidad de que te guste este anime."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en predicción: {str(e)}")


@app.get("/api/joyas-ocultas")
def joyas_ocultas(id_usuario: int = None, limit: int = 10):
    """
    Endpoint de joyas ocultas (Clustering).
    Usa la columna 'cluster_kmeans' que ya existe en el dataset.
    """
    
    # 1. Verificar si tenemos la columna cluster_kmeans
    if 'cluster_kmeans' not in df_clustering.columns:
        return {
            "hidden_gems": [], 
            "mensaje": "El dataset no tiene la columna 'cluster_kmeans'. Verifica tu archivo final_anime_dataset_clustering."
        }

    # 2. Filtrar animes (Únicos y por Cluster 1)
    # NOTA: Usamos .copy() para evitar warnings de Pandas
    df_candidatos = df_clustering.drop_duplicates(subset=['id_anime']).copy()

    # --- FILTRO CLUSTER ---
    # Aquí buscamos explícitamente el grupo 1
    # Si ves que sale vacío, prueba cambiar el número (0, 1, 2, 3...)
    df_joyas = df_candidatos[df_candidatos['cluster_kmeans'] == 1].copy()

    print(f"DEBUG Clustering: Encontrados {len(df_joyas)} animes en cluster 1")

    if df_joyas.empty:
        return {"hidden_gems": [], "mensaje": "El cluster 1 está vacío. Intenta re-entrenar o cambiar de cluster."}

    # 3. Filtrar vistos por el usuario
    if id_usuario:
        # Usamos df_clasificacion para ver qué ha visto el usuario (historial completo)
        df_historial = df_clasificacion[df_clasificacion["id_usuario"] == id_usuario]
        if not df_historial.empty:
            vistos = set(df_historial["id_anime"].unique())
            df_joyas = df_joyas[~df_joyas["id_anime"].isin(vistos)]

    # 4. Ordenar y Formatear
    # Ordenamos por puntuación para mostrar las mejores joyas primero
    if 'puntuacion' in df_joyas.columns:
        df_joyas = df_joyas.sort_values("puntuacion", ascending=False)
    
    # Agregar imágenes
    df_joyas = agregar_imagenes_csv(df_joyas)

    # Columnas a devolver
    COLUMNAS_FRONT = ["id_anime", "titulo_anime", "nombre_anime", "puntuacion", "total_episodios", "popularidad", "image_url"]
    cols_existentes = [c for c in COLUMNAS_FRONT if c in df_joyas.columns]
    
    resultado = df_joyas[cols_existentes].head(limit).to_dict(orient="records")

    return {"hidden_gems": resultado}


@app.get("/api/mi-lista")
def get_mi_lista(id_usuario: int = id_usuario, limit: int = 10):
    df_animes_usuario = df_clasificacion[df_clasificacion["id_usuario"] == id_usuario].copy()

    if df_animes_usuario.empty:
        raise HTTPException(status_code=404, detail=f"Usuario {id_usuario} no tiene interacciones.")

    COLUMNAS_RESPUESTA = ["id_anime", "titulo_anime", "puntuacion_usuario", "nombre_anime", "puntuacion", "total_episodios", "popularidad", "favoritos", "sinopsis"]
    
    df_respuesta = df_animes_usuario.sort_values("puntuacion_usuario", ascending=False).copy()
    
    cols_finales = [col for col in COLUMNAS_RESPUESTA if col in df_respuesta.columns]
    df_respuesta = df_respuesta[cols_finales]
    
    df_respuesta = agregar_imagenes_csv(df_respuesta)
    animes_lista = df_respuesta.head(limit).to_dict(orient="records")

    return {"animes": animes_lista}

# =====================================================================
# 5. ENDPOINTS ADMIN
# =====================================================================

class ConsultaLocal(BaseModel):
    nombre_anime: str

@app.post("/api/admin/demo-local")
def demo_prediccion_local(consulta: ConsultaLocal):
    try:
        nombre_busqueda = consulta.nombre_anime.lower().strip()
        
        # 1. Buscar en DataFrame local
        df_unico = df_regresion.drop_duplicates(subset=['id_anime'])
        
        if 'titulo_anime' in df_unico.columns:
            col_titulo = 'titulo_anime'
        elif 'nombre_anime' in df_unico.columns:
            col_titulo = 'nombre_anime'
        else:
            col_titulo = df_unico.columns[0] 

        mascara = df_unico[col_titulo].astype(str).str.lower().str.contains(nombre_busqueda)
        resultados = df_unico[mascara]

        if resultados.empty:
            raise HTTPException(status_code=404, detail=f"Anime '{consulta.nombre_anime}' no encontrado en el dataset local.")

        anime_row = resultados.iloc[0]
        
        # 2. Preparar datos
        datos_prediccion = pd.DataFrame([anime_row[FEATURES_REGRESION_FINALES]])
        
        # 3. Escalar y Predecir
        X_escalado = scaler_regresion.transform(datos_prediccion)
        raw_prediccion = modelo_regresion.predict(X_escalado)[0]
        
        # --- CONVERSIÓN A TIPOS NATIVOS PYTHON ---
        rating_predicho = float(raw_prediccion) 
        es_recomendable = bool(rating_predicho >= 7.5)
        
        episodios = int(anime_row.get('total_episodios', 0))
        popularidad = int(anime_row.get('popularidad', 0))
        favoritos = int(anime_row.get('favoritos', 0))
        id_anime = int(anime_row['id_anime'])
        titulo = str(anime_row[col_titulo])

        # 4. Imagen
        imagen_url = "/static/img/imagen_no_encontrada.png"
        try:
            if 'anime_id' in df_imagenes.columns:
                img_row = df_imagenes[df_imagenes['anime_id'] == id_anime]
                if not img_row.empty:
                    imagen_url = img_row.iloc[0]['image_url']
        except Exception:
            pass

        return {
            "titulo": titulo,
            "id_anime": id_anime,
            "features_clave": {
                "Episodios": episodios,
                "Popularidad": popularidad,
                "Favoritos": favoritos
            },
            "rating_predicho": round(rating_predicho, 2),
            "es_recomendable": es_recomendable,
            "imagen": imagen_url,
            "mensaje": "Simulación exitosa usando datos locales."
        }

    except KeyError as e:
        print(f"Error Key: {e}")
        raise HTTPException(status_code=500, detail=f"Error de columnas: Falta {e}")
    except Exception as e:
        print(f"Error General: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request):
    return templates.TemplateResponse("admin.html", {"request": request})

@app.get("/health")
def health_check():
    return {"status": "healthy", "version": "2.0.0", "ml_models_loaded": True}