# backend/main.py
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import io
import pandas as pd
import psycopg2
import json
import os
from playwright.sync_api import sync_playwright

from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuración desde .env
DB_CONFIG = {
    "host": os.getenv("DB_HOST"),
    "port": os.getenv("DB_PORT"),
    "database": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASSWORD")
}

def get_connection():
    return psycopg2.connect(**DB_CONFIG)





"""
@app.get("/verificar_paises_sancionados")
def verificar_paises_sancionados():
    # 1. Scraping
    paises_scrapeados = scrapear_paises_sancionados()

    # 2. Obtener países de la tabla
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT nombre FROM paises_organizacion")
    paises_org = [row[0].strip() for row in cur.fetchall()]
    cur.close()
    conn.close()

    # 3. Comparar
    en_sancion = [p for p in paises_org if p in paises_scrapeados]
    return {"en_sancion": en_sancion, "cantidad": len(en_sancion)} """

@app.post("/export_excel")
async def export_excel(request: Request):
    data = await request.json()
    selected_tables = data.get("tables", [])
    if not selected_tables:
        return {"error": "No tables selected"}

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        conn = get_connection()
        for table in selected_tables:
            df = pd.read_sql_query(f"SELECT * FROM {table}", conn)
            df.to_excel(writer, sheet_name=table[:31], index=False)
        conn.close()

    output.seek(0)
    return StreamingResponse(output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=datos_auditoria.xlsx"}
    )




@app.get("/controles")
def get_controles():
    def calcular_estado(cantidad):
        if cantidad > 15:
            return "Crítico"
        elif cantidad > 0:
            return "Atención"
        else:
            return "Cumpliendo" # sin anomalias detectadas

    conn = get_connection()
    cur = conn.cursor()

    # Obtener todos los controles
    cur.execute("SELECT * FROM controles")
    rows = cur.fetchall()
    columns = [desc[0] for desc in cur.description]
    controles = [dict(zip(columns, row)) for row in rows]

    # Para cada control, contar anomalías en su tabla correspondiente
    for control in controles:
        control_id = control["id"]
        tabla_resultado = f"resultados_control{control_id}"

        try:
            cur.execute(f"SELECT COUNT(*) FROM {tabla_resultado}")
            cantidad_anomalias = cur.fetchone()[0]
        except Exception:
            cantidad_anomalias = 0  # Si la tabla no existe o hay error

        # Guardamos el conteo
        control["cantidadAnomalias"] = cantidad_anomalias

        # Si hay anomalías, recalculamos el estado
        if cantidad_anomalias > 0:
            control["estado"] = calcular_estado(cantidad_anomalias)
        else:
            control["estado"] = "Cumpliendo"
            control["accion_requerida"] = None  # Si esta cumpliendo no deberian existir anomalias

    cur.close()
    conn.close()
    return controles


