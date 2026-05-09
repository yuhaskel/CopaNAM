import os
import json
import shutil
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app = FastAPI()

# --- CONFIGURACIÓN DE RUTAS Y PERSISTENCIA ---
# Render usa la variable de entorno 'RENDER'. Si no existe, estamos en local.
IS_RENDER = os.environ.get("RENDER", False)
PERSISTENT_DIR = "/data" if IS_RENDER else "."
DATA_FILE = os.path.join(PERSISTENT_DIR, "torneo_data.json")
LOCAL_SOURCE = "torneo_data.json"

# Lógica de primera ejecución: Copiar el JSON base al disco persistente si no existe
if IS_RENDER and not os.path.exists(DATA_FILE):
    try:
        if os.path.exists(LOCAL_SOURCE):
            shutil.copy(LOCAL_SOURCE, DATA_FILE)
            print(f"--> [INIT] Archivo inicial copiado a {DATA_FILE}")
        else:
            # Si ni siquiera existe el local, creamos uno vacío estructuralmente
            with open(DATA_FILE, "w", encoding='utf-8') as f:
                json.dump({"equipos": {}, "partidos": [], "goleadores": []}, f)
            print("--> [INIT] Creado archivo JSON vacío en disco persistente")
    except Exception as e:
        print(f"--> [ERROR INIT] No se pudo inicializar el disco: {e}")

# --- MIDDLEWARE ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- ENDPOINTS ---

# 1. Servir la página principal
@app.get("/")
async def inicio():
    return FileResponse('index.html')

# 2. Servir el JSON desde el disco persistente (para que el script.js lo lea)
@app.get("/torneo_data.json")
async def obtener_datos():
    if os.path.exists(DATA_FILE):
        return FileResponse(DATA_FILE)
    raise HTTPException(status_code=404, detail="Archivo de datos no encontrado")

# 3. Guardar datos en el disco persistente
@app.post("/guardar")
async def guardar_datos(request: Request):
    try:
        data = await request.json()
        with open(DATA_FILE, "w", encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        
        print(f"--> ¡Datos guardados en {DATA_FILE}!")
        return {"status": "success"}
    except Exception as e:
        print(f"--> Error al guardar: {e}")
        raise HTTPException(status_code=400, detail="Error al procesar el JSON")

# --- ARCHIVOS ESTÁTICOS ---
# Esto sirve el CSS, JS e imágenes. 
# Importante: debe ir al final para no interferir con las rutas anteriores.
app.mount("/", StaticFiles(directory="./"), name="static")
