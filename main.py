import os
import json
import shutil
from fastapi import FastAPI, HTTPException, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app = FastAPI()

# --- CONFIGURACIÓN DE RUTAS Y PERSISTENCIA ---
IS_RENDER = os.environ.get("RENDER", False)
PERSISTENT_DIR = "/data" if IS_RENDER else "."
DATA_FILE = os.path.join(PERSISTENT_DIR, "torneo_data.json")
LOGOS_DIR = os.path.join(PERSISTENT_DIR, "logos") # Carpeta para escudos
LOCAL_SOURCE = "torneo_data.json"

# Crear carpetas necesarias en el disco persistente
if not os.path.exists(LOGOS_DIR):
    os.makedirs(LOGOS_DIR, exist_ok=True)
    print(f"--> [INIT] Carpeta de logos creada en {LOGOS_DIR}")

# Lógica de primera ejecución: Copiar el JSON base si no existe
if IS_RENDER and not os.path.exists(DATA_FILE):
    try:
        if os.path.exists(LOCAL_SOURCE):
            shutil.copy(LOCAL_SOURCE, DATA_FILE)
            print(f"--> [INIT] Archivo inicial copiado a {DATA_FILE}")
        else:
            with open(DATA_FILE, "w", encoding='utf-8') as f:
                json.dump({"equipos": {}, "partidos": [], "goleadores": []}, f)
            print("--> [INIT] Creado archivo JSON vacío")
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

# 2. LOGIN SEGURO (NUEVO)
# Este endpoint recibe la clave del frontend y la compara con la variable de entorno
@app.post("/login")
async def login(request: Request):
    try:
        data = await request.json()
        password_enviada = data.get("password")
        
        # Obtenemos la clave secreta configurada en el panel de Render
        # Si no existe, usamos una por defecto para pruebas locales
        password_real = os.environ.get("ADMIN_PASSWORD", "organizadores2026")
        
        if password_enviada == password_real:
            return {"status": "success", "auth": True}
        else:
            # Si la clave es incorrecta, devolvemos un error 401 (No autorizado)
            raise HTTPException(status_code=401, detail="Clave incorrecta")
    except Exception as e:
        raise HTTPException(status_code=400, detail="Error en el formato de datos")

# 3. Servir el JSON desde el disco persistente
@app.get("/torneo_data.json")
async def obtener_datos():
    if os.path.exists(DATA_FILE):
        return FileResponse(DATA_FILE)
    raise HTTPException(status_code=404, detail="Archivo de datos no encontrado")

# 4. Guardar datos en el disco persistente
@app.post("/guardar")
async def guardar_datos(request: Request):
    try:
        data = await request.json()
        with open(DATA_FILE, "w", encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# 5. SUBIR LOGOS
@app.post("/upload_logo")
async def upload_logo(file: UploadFile = File(...)):
    try:
        filename = file.filename.replace(" ", "_")
        file_path = os.path.join(LOGOS_DIR, filename)
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        return {"logo_url": f"/logos/{filename}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al subir logo: {e}")

# 6. SERVIR LOGOS
@app.get("/logos/{filename}")
async def get_logo(filename: str):
    file_path = os.path.join(LOGOS_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path)
    raise HTTPException(status_code=404, detail="Imagen no encontrada")

# --- ARCHIVOS ESTÁTICOS ---
app.mount("/", StaticFiles(directory="./"), name="static")
