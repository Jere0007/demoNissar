import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import httpx
import csv
import io

# Cargar las variables de entorno desde el archivo .env local
load_dotenv()

# Leer la clave de la NASA de forma segura desde el entorno
FIRMS_MAP_KEY = os.getenv("FIRMS_MAP_KEY")

app = FastAPI(
    title="NISAR Surface Change Explorer API",
    description="Backend dinámico integrado con variables de entorno para consultas basadas en coordenadas del mapa",
    version="2.1"
)

# Configurar CORS para permitir la comunicación con el frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "¡API dinámica lista para el mapa interactivo! 🛰️"}


# ==========================================
# 1. MÓDULO DE INCENDIOS (NASA FIRMS) - Dinámico por coordenadas y días
# ==========================================
@app.get("/api/fires")
async def get_fires(lat: float = 14.6, lon: float = -90.5, delta: float = 2.0, days: int = 1):
    """
    Recibe lat, lon, el radio (delta) y los días hacia atrás (days) 
    para consultar incendios activos de forma dinámica.
    """
    if not FIRMS_MAP_KEY:
        raise HTTPException(status_code=500, detail="La variable de entorno FIRMS_MAP_KEY no está configurada.")

    west = lon - delta
    east = lon + delta
    south = lat - delta
    north = lat + delta
    bbox = f"{west},{south},{east},{north}"
    
    url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{FIRMS_MAP_KEY}/VIIRS_NOAA20_NRT/{bbox}/{days}"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url)
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail="Error al conectar con NASA FIRMS")
            
            decoded_content = response.content.decode('utf-8')
            csv_reader = csv.DictReader(io.StringIO(decoded_content))
            fires_list = list(csv_reader)
            
            return {
                "source": "NASA FIRMS",
                "searched_point": {"lat": lat, "lon": lon},
                "days_back": days,
                "total_detections": len(fires_list),
                "data": fires_list
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# 2. MÓDULO DE SISMOS (USGS) - Dinámico por radio cercano
# ==========================================
@app.get("/api/earthquakes")
async def get_earthquakes(lat: float = 14.6, lon: float = -90.5, radius_km: float = 250.0):
    """
    Consulta sismos cercanos a las coordenadas elegidas en el mapa 
    utilizando el parámetro de radio del USGS.
    """
    url = f"https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson&latitude={lat}&longitude={lon}&maxradiuskm={radius_km}&orderby=time"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url)
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail="Error al conectar con USGS")
            
            data = response.json()
            return {
                "source": "USGS Earthquake Hazards",
                "searched_point": {"lat": lat, "lon": lon},
                "radius_km": radius_km,
                "total_events": data.get("metadata", {}).get("count", 0),
                "data": data.get("features", [])
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


# ==========================================
# 3. MÓDULO DE PRECIPITACIÓN (NASA POWER) - Dinámico por coordenadas
# ==========================================
@app.get("/api/precipitation")
async def get_precipitation(lat: float = 14.6, lon: float = -90.5):
    """
    Obtiene los datos meteorológicos/precipitación exactamente 
    para la latitud y longitud donde el usuario hizo clic.
    """
    url = f"https://power.larc.nasa.gov/api/temporal/daily/point?parameters=PRECTOTCORR&community=RE&longitude={lon}&latitude={lat}&start=20260101&end=20260110&format=JSON"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url)
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail="Error al conectar con NASA POWER")
            
            return {
                "source": "NASA POWER",
                "searched_point": {"lat": lat, "lon": lon},
                "data": response.json()
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))