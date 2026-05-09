from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import json

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/guardar")
async def guardar_datos(request: Request):
    try:
        # Extraemos el JSON crudo de la petición
        data = await request.json()
        
        with open("torneo_data.json", "w", encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        
        print("--> ¡Datos guardados correctamente!")
        return {"status": "success"}
    except Exception as e:
        print(f"--> Error: {e}")
        raise HTTPException(status_code=400, detail="El formato JSON es inválido")

@app.get("/")
async def inicio():
    return {"mensaje": "Servidor funcionando"}