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
LOGOS_DIR = os.path.join(PERSISTENT_DIR, "logos") 
PRONOSTICOS_DIR = os.path.join(PERSISTENT_DIR, "pronosticos") 
RESULTADOS_CARTILLA_FILE = os.path.join(PERSISTENT_DIR, "cartilla_resultados.json")
LOCAL_SOURCE = "torneo_data.json"

# LISTA REAL Y EXACTA DE LOS 20 PARTIDOS DEL MUNDIAL DE LAS CARTILLAS
PARTIDOS_MUNDIAL_LIST = [
    "México VS Sudáfrica", "Brasil VS Marruecos", "Países Bajos VS Japón", "Costa de Marfil VS Ecuador",
    "Francia VS Senegal", "Argelia VS Argentina", "Inglaterra VS Croacia", "México VS Corea del Sur",
    "Turquía VS Paraguay", "Países Bajos VS Suecia", "Alemania VS Costa de Marfil", "Argentina VS Austria",
    "Noruega VS Senegal", "Brasil VS Escocia", "Ecuador VS Alemania", "Turquía VS EEUU", 
    "Paraguay VS Australia", "Noruega VS Francia", "Uruguay VS España", "Colombia VS Portugal"
]

# Crear carpetas necesarias en el disco persistente de Render o local
if not os.path.exists(LOGOS_DIR):
    os.makedirs(LOGOS_DIR, exist_ok=True)

if not os.path.exists(PRONOSTICOS_DIR):
    os.makedirs(PRONOSTICOS_DIR, exist_ok=True)

# Inicializar archivo de resultados de la cartilla si no existe
if not os.path.exists(RESULTADOS_CARTILLA_FILE):
    with open(RESULTADOS_CARTILLA_FILE, "w", encoding='utf-8') as f:
        json.dump({}, f)

# Lógica de primera ejecución: Copiar el JSON base si no existe
if IS_RENDER and not os.path.exists(DATA_FILE):
    try:
        if os.path.exists(LOCAL_SOURCE):
            shutil.copy(LOCAL_SOURCE, DATA_FILE)
        else:
            with open(DATA_FILE, "w", encoding='utf-8') as f:
                json.dump({"equipos": {}, "partidos": [], "goleadores": []}, f)
    except Exception as e:
        print(f"--> [ERROR INIT] No se pudo inicializar el disco: {e}")

# --- MIDDLEWARE (Habilita CORS para conectar tu html local con Render) ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- LÓGICA DE CÁLCULO ---
def calcular_puntos_cartilla(predicciones, reales):
    puntos_totales = 0
    aciertos_exactos = 0
    
    for pred in predicciones:
        llave_partido = f"{pred['local']} VS {pred['visita']}"
        
        if llave_partido not in reales or reales[llave_partido].get("goles_local") is None:
            continue
            
        gl_p, gv_p = int(pred["goles_local"]), int(pred["goles_visita"])
        gl_r = int(reales[llave_partido]["goles_local"])
        gv_r = int(reales[llave_partido]["goles_visita"])
        
        if gl_p == gl_r and gv_p == gv_r:
            puntos_totales += 3
            aciertos_exactos += 1
        else:
            tendencia_pred = 1 if gl_p > gv_p else (2 if gl_p < gv_p else 0)
            tendencia_real = 1 if gl_r > gv_r else (2 if gl_r < gv_r else 0)
            if tendencia_pred == tendencia_real:
                puntos_totales += 1
                
    return puntos_totales, aciertos_exactos

# --- ENDPOINTS LIGA LOCAL ---

@app.get("/")
async def home():
    return FileResponse("index.html")

@app.post("/login")
async def login(request: Request):
    try:
        data = await request.json()
        password_enviada = data.get("password")
        password_real = os.environ.get("ADMIN_PASSWORD", "NAM...2026")
        
        if password_enviada == password_real:
            return {"status": "success", "auth": True}
        else:
            raise HTTPException(status_code=401, detail="Clave incorrecta")
    except Exception as e:
        raise HTTPException(status_code=400, detail="Error en el formato de datos")

@app.get("/torneo_data.json")
async def obtener_datos(rama: str = "masculina"):
    # Por ahora procesa y sirve el archivo único actual para no interrumpir el flujo en vivo
    if os.path.exists(DATA_FILE):
        return FileResponse(DATA_FILE)
    raise HTTPException(status_code=404, detail="Archivo de datos no encontrado")

@app.post("/guardar")
async def guardar_datos(request: Request):
    try:
        data = await request.json()
        with open(DATA_FILE, "w", encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

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

@app.get("/logos/{filename}")
async def get_logo(filename: str):
    file_path = os.path.join(LOGOS_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(file_path)
    raise HTTPException(status_code=404, detail="Imagen no encontrada")

# --- ENDPOINTS CARTILLA MUNDIAL ---

@app.get("/api/cartilla-resultados")
async def get_cartilla_resultados():
    if os.path.exists(RESULTADOS_CARTILLA_FILE):
        with open(RESULTADOS_CARTILLA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

@app.post("/api/cartilla-guardar-resultados")
async def guardar_cartilla_resultados(request: Request):
    try:
        data = await request.json()
        with open(RESULTADOS_CARTILLA_FILE, "w", encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/ranking-cartilla")
async def obtener_ranking():
    ranking = []
    reales = {}
    if os.path.exists(RESULTADOS_CARTILLA_FILE):
        with open(RESULTADOS_CARTILLA_FILE, "r", encoding="utf-8") as f:
            reales = json.load(f)
            
    try:
        if os.path.exists(PRONOSTICOS_DIR):
            for archivo in os.listdir(PRONOSTICOS_DIR):
                if archivo.endswith(".json"):
                    with open(os.path.join(PRONOSTICOS_DIR, archivo), "r", encoding="utf-8") as f:
                        datos = json.load(f)
                        puntos, exactos = calcular_puntos_cartilla(datos.get("predicciones", []), reales)
                        
                        ranking.append({
                            "nombre": datos.get("nombre", "Anónimo"),
                            "curso": datos.get("curso_estamento", "N/A"),
                            "campeon": datos.get("campeon_del_mundo", "No elegido"),
                            "puntos": puntos,
                            "exactos": exactos
                        })  
        ranking.sort(key=lambda x: (x["puntos"], x["exactos"]), reverse=True)
        
        # 👇 ESTA ES LA LÍNEA CLAVE QUE DEBES CAMBIAR 👇
        return {"ranking": ranking, "reales": reales} 
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
# --- ENLACE DIRECTO DE CARGA MASIVA (SIN CONTRASEÑA) ---
@app.post("/api/admin/subir-mis-json-locales")
async def subir_mis_json_locales(files: list[UploadFile] = File(...)):
    if not os.path.exists(PRONOSTICOS_DIR):
        os.makedirs(PRONOSTICOS_DIR, exist_ok=True)
        
    subidos = 0
    for file in files:
        if file.filename.endswith(".json"):
            file_path = os.path.join(PRONOSTICOS_DIR, file.filename)
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            subidos += 1
            
    return {"status": "success", "mensaje": f"¡Éxito! Se guardaron {subidos} cartillas en la carpeta /data/pronosticos de Render."}

app.mount("/", StaticFiles(directory="./"), name="static")
