import os
import json
import shutil
from fastapi import FastAPI, HTTPException, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app = FastAPI()

# Permmitir CORS para desarrollo local y producción
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- CONFIGURACIÓN DE RUTAS Y PERSISTENCIA ---
IS_RENDER = os.environ.get("RENDER", False)
PERSISTENT_DIR = "/data" if IS_RENDER else "."

# 1. Rutas de Archivos por Rama
DATA_FILE_MASCULINA = os.path.join(PERSISTENT_DIR, "torneo_data.json") # Mantiene tu archivo intacto
DATA_FILE_FEMENINA = os.path.join(PERSISTENT_DIR, "torneo_data_femenina.json") # Archivo nuevo

LOGOS_DIR = os.path.join(PERSISTENT_DIR, "logos") 
PRONOSTICOS_DIR = os.path.join(PERSISTENT_DIR, "pronosticos") 
RESULTADOS_CARTILLA_FILE = os.path.join(PERSISTENT_DIR, "cartilla_resultados.json")

# Función auxiliar para garantizar que exista una estructura base si el JSON femenino está vacío
def garantizar_estructura_base(ruta_archivo):
    if not os.path.exists(ruta_archivo):
        plantilla_vacia = {
            "equipos": [],
            "partidos": [],
            "goleadores": []
        }
        with open(ruta_archivo, "w", encoding="utf-8") as f:
            json.dump(plantilla_vacia, f, indent=4, ensure_ascii=False)

# Garantizar carpetas bases obligatorias
for carpeta in [LOGOS_DIR, PRONOSTICOS_DIR]:
    if not os.path.exists(carpeta):
        os.makedirs(carpeta, exist_ok=True)

# LISTA REAL Y EXACTA DE LOS 20 PARTIDOS DEL MUNDIAL DE LAS CARTILLAS
PARTIDOS_MUNDIAL_LIST = [
    "México VS Sudáfrica", "Brasil VS Marruecos", "Países Bajos VS Japón", "Costa de Marfil VS Ecuador",
    "Francia VS Senegal", "Argelia VS Argentina", "Inglaterra VS Croacia", "México VS Corea del Sur",
    "Turquía VS Paraguay", "Países Bajos VS Suecia", "Alemania VS Costa de Marfil", "Argentina VS Austria",
    "Noruega VS Senegal", "Brasil VS Escocia", "Ecuador VS Alemania", "Turquía VS EEUU", 
    "Paraguay VS Australia", "Noruega VS Francia", "Uruguay VS España", "Colombia VS Portugal"
]

# --- ENDPOINTS ADAPTADOS PARA RAMAS (MASCULINA / FEMENINA) ---

@app.get("/torneo_data.json")
async def obtener_datos(rama: str = "masculina"):
    """Devuelve el JSON correspondiente según la rama solicitada en la URL (?rama=femenina)"""
    if rama == "femenina":
        garantizar_estructura_base(DATA_FILE_FEMENINA)
        return FileResponse(DATA_FILE_FEMENINA)
    else:
        # Por defecto o rama 'masculina', lee el archivo clásico e histórico
        if os.path.exists(DATA_FILE_MASCULINA):
            return FileResponse(DATA_FILE_MASCULINA)
        raise HTTPException(status_code=404, detail="Archivo de datos masculino no encontrado")

@app.post("/api/guardar")
async def guardar_datos(request: Request, rama: str = "masculina"):
    """Guarda las configuraciones y resultados en el JSON correspondiente sin mezclar ramas"""
    try:
        nuevos_datos = await request.json()
        archivo_destino = DATA_FILE_FEMENINA if rama == "femenina" else DATA_FILE_MASCULINA
        
        with open(archivo_destino, "w", encoding="utf-8") as f:
            json.dump(nuevos_datos, f, indent=4, ensure_ascii=False)
        return {"status": "success", "message": f"Datos guardados correctamente en la rama {rama}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/admin/subir-logo")
async def subir_logo(file: UploadFile = File(...)):
    """Sube los logos de los equipos (Compartido de forma segura para ambas ramas)"""
    try:
        file_path = os.path.join(LOGOS_DIR, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        return {"status": "success", "filename": file.filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- ENDPOINTS COMPARTIDOS (CARTILLA MUNDIAL Y OTROS) ---

@app.get("/api/cartilla/resultados-reales")
async def obtener_resultados_reales_cartilla():
    if os.path.exists(RESULTADOS_CARTILLA_FILE):
        return FileResponse(RESULTADOS_CARTILLA_FILE)
    return {"resultados": {}}

@app.post("/api/cartilla/guardar-reales")
async def guardar_resultados_reales_cartilla(request: Request):
    try:
        datos = await request.json()
        with open(RESULTADOS_CARTILLA_FILE, "w", encoding="utf-8") as f:
            json.dump(datos, f, indent=4, ensure_ascii=False)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/cartilla/enviar-pronostico")
async def enviar_pronostico(request: Request):
    try:
        datos = await request.json()
        nombre = datos.get("nombre", "").strip().replace(" ", "_")
        curso = datos.get("curso_estamento", "").strip().replace(" ", "_")
        
        if not nombre or not curso:
            raise HTTPException(status_code=400, detail="Nombre o Curso inválidos")
            
        filename = f"{nombre}_{curso}.json"
        file_path = os.path.join(PRONOSTICOS_DIR, filename)
        
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(datos, f, indent=4, ensure_ascii=False)
            
        return {"status": "success", "message": "Pronóstico guardado exitosamente"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/cartilla/ranking")
async def obtener_ranking_cartilla():
    try:
        reales = {}
        if os.path.exists(RESULTADOS_CARTILLA_FILE):
            with open(RESULTADOS_CARTILLA_FILE, "r", encoding="utf-8") as f:
                reales = json.load(f).get("resultados", {})
                
        ranking = []
        if os.path.exists(PRONOSTICOS_DIR):
            for archivo in os.listdir(PRONOSTICOS_DIR):
                if archivo.endswith(".json"):
                    ruta_p = os.path.join(PRONOSTICOS_DIR, archivo)
                    with open(ruta_p, "r", encoding="utf-8") as f:
                        datos = json.load(f)
                        pronosticos = datos.get("pronosticos", {})
                        
                        puntos = 0
                        exactos = 0
                        
                        for p in PARTIDOS_MUNDIAL_LIST:
                            real_m = reales.get(p)
                            prono_m = pronosticos.get(p)
                            
                            if real_m and prono_m:
                                g_r_l = real_m.get("goles_local")
                                g_r_v = real_m.get("goles_visita")
                                g_p_l = prono_m.get("goles_local")
                                g_p_v = prono_m.get("goles_visita")
                                
                                if g_r_l is not None and g_r_v is not None and g_p_l is not None and g_p_v is not None:
                                    try:
                                        gr_l, gr_v = int(g_r_l), int(g_r_v)
                                        gp_l, gp_v = int(g_p_l), int(g_p_v)
                                        
                                        if gr_l == gp_l and gr_v == gp_v:
                                            puntos += 3
                                            exactos += 1
                                        elif (gr_l > gr_v and gp_l > gp_v) or (gr_l < gr_v and gp_l < gp_v) or (gr_l == gr_v and gp_l == gp_v):
                                            puntos += 1
                                    except:
                                        continue
                                        
                        ranking.append({
                            "nombre": datos.get("nombre", "Anónimo"),
                            "curso": datos.get("curso_estamento", "N/A"),
                            "campeon": datos.get("campeon_del_mundo", "No elegido"),
                            "puntos": puntos,
                            "exactos": exactos
                        })  
        ranking.sort(key=lambda x: (x["puntos"], x["exactos"]), reverse=True)
        return {"ranking": ranking, "reales": reales} 
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/admin/subir-mis-json-locales")
async def subir_json_locales_manual(files: list[UploadFile] = File(...)):
    subidos = 0
    for file in files:
        if file.filename.endswith(".json"):
            file_path = os.path.join(PRONOSTICOS_DIR, file.filename)
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            subidos += 1
    return {"status": "success", "archivos_subidos": subidos}

# Montar los archivos estáticos de la interfaz web
app.mount("/", StaticFiles(directory=".", html=True), name="static")
